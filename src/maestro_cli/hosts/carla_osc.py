"""
Carla OSC Client - Low-level OSC communication with Carla
Uses python-osc for sending/receiving messages to Carla's OSC interface.
"""

import logging
import socket
import subprocess
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from pythonosc import udp_client, osc_server, dispatcher

from maestro_cli.config import settings

logger = logging.getLogger(__name__)


class CarlaOSCError(Exception):
    """Base error for Carla OSC communication"""
    pass


class CarlaOSCTimeoutError(CarlaOSCError):
    """Timeout waiting for Carla response"""
    pass


class CarlaOSCConnectionError(CarlaOSCError):
    """Cannot connect to Carla OSC server"""
    pass


class CarlaOSCClient:
    """
    Low-level OSC client for communicating with Carla.

    Handles:
    - Sending OSC messages to Carla
    - Receiving OSC responses via a listener
    - Connection detection and health checks
    - Timeout management
    - Full logging of all OSC communication
    """

    # Standard Carla OSC addresses
    ADDR_ADD_PLUGIN = "/carla/load_plugin"
    ADDR_REMOVE_PLUGIN = "/carla/remove_plugin"
    ADDR_LOAD_PRESET = "/carla/load_preset"
    ADDR_SET_PARAMETER = "/carla/set_parameter_value"
    ADDR_GET_PARAMETER = "/carla/get_parameter_value"
    ADDR_SET_VOLUME = "/carla/set_volume"
    ADDR_SET_PAN = "/carla/set_panning"
    ADDR_CONNECT = "/carla/patchbay_connect"
    ADDR_DISCONNECT = "/carla/patchbay_disconnect"
    ADDR_TRANSPORT_PLAY = "/carla/transport_play"
    ADDR_TRANSPORT_STOP = "/carla/transport_stop"
    ADDR_TRANSPORT_PAUSE = "/carla/transport_pause"
    ADDR_RENDER = "/carla/render"
    ADDR_PING = "/carla/ping"

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9001,
        timeout: float = 5.0,
        listen_port: int = 9998,
    ):
        """
        Initialize the OSC client for Carla.

        Args:
            host: Carla OSC host address
            port: Carla OSC port
            timeout: Default timeout for operations in seconds
            listen_port: Port to listen for responses from Carla
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.listen_port = listen_port

        self._client: Optional[udp_client.SimpleUDPClient] = None
        self._listener_server: Optional[osc_server.ThreadingOSCUDPServer] = None
        self._listener_thread: Optional[threading.Thread] = None
        self._responses: Dict[str, Any] = {}
        self._response_events: Dict[str, threading.Event] = {}
        self._connected = False

        logger.info(
            "CarlaOSCClient initialized: host=%s, port=%d, timeout=%.1fs",
            host, port, timeout,
        )

    def connect(self) -> bool:
        """
        Establish OSC connection to Carla.

        Returns:
            True if connection succeeded
        """
        try:
            self._client = udp_client.SimpleUDPClient(self.host, self.port)
            self._start_listener()
            self._connected = True
            logger.info("OSC client connected to %s:%d", self.host, self.port)
            return True
        except Exception as e:
            logger.error("Failed to connect OSC client: %s", e)
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect and clean up resources"""
        self._stop_listener()
        self._client = None
        self._connected = False
        logger.info("OSC client disconnected")

    def send(self, address: str, *args: Any) -> bool:
        """
        Send an OSC message to Carla.

        Args:
            address: OSC address (e.g. /carla/load_plugin)
            *args: Message arguments

        Returns:
            True if message was sent successfully
        """
        if self._client is None:
            if not self.connect():
                logger.error("Cannot send: not connected to Carla")
                return False

        try:
            self._client.send_message(address, list(args))
            logger.debug("OSC sent: %s %s", address, args)
            return True
        except Exception as e:
            logger.error("OSC send failed: %s %s -> %s", address, args, e)
            return False

    def send_and_wait(
        self,
        address: str,
        *args: Any,
        response_address: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Optional[Any]:
        """
        Send an OSC message and wait for a response.

        Args:
            address: OSC address to send to
            *args: Message arguments
            response_address: Address to listen for response (defaults to address + "/reply")
            timeout: Timeout in seconds (defaults to self.timeout)

        Returns:
            Response data or None on timeout
        """
        timeout = timeout or self.timeout
        resp_addr = response_address or f"{address}/reply"

        # Set up response event
        event = threading.Event()
        self._response_events[resp_addr] = event
        self._responses.pop(resp_addr, None)

        # Send the message
        if not self.send(address, *args):
            return None

        # Wait for response
        if event.wait(timeout=timeout):
            response = self._responses.pop(resp_addr, None)
            logger.debug("OSC response received for %s: %s", resp_addr, response)
            return response
        else:
            logger.warning(
                "OSC timeout (%.1fs) waiting for response on %s", timeout, resp_addr
            )
            self._response_events.pop(resp_addr, None)
            return None

    def is_connected(self) -> bool:
        """
        Check if Carla is responding on the OSC port.

        Returns:
            True if Carla is reachable
        """
        # First try a UDP ping via OSC
        if self._client is not None:
            try:
                self.send(self.ADDR_PING)
                # For UDP we can't truly verify delivery, so also check port
            except Exception:
                pass

        # Check if the port is open (TCP fallback check)
        return self._check_port_open()

    def _check_port_open(self) -> bool:
        """Check if the OSC port is reachable"""
        try:
            # Try UDP socket probe
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            sock.sendto(b"", (self.host, self.port))
            sock.close()
            return True
        except (socket.error, OSError):
            return False

    def start_carla(
        self,
        carla_cmd: Optional[str] = None,
        wait: bool = True,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        Start the Carla server process.

        Args:
            carla_cmd: Path to Carla executable (defaults to settings)
            wait: Wait for Carla to be ready
            timeout: Max wait time in seconds

        Returns:
            True if Carla started successfully
        """
        carla_cmd = carla_cmd or settings.CARLA_START_CMD
        timeout = timeout or self.timeout * 2  # Give extra time for startup

        logger.info("Starting Carla: %s --osc-port %d", carla_cmd, self.port)

        try:
            process = subprocess.Popen(
                [carla_cmd, "--osc-port", str(self.port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
            )

            if not wait:
                logger.info("Carla process started (PID %d), not waiting", process.pid)
                return True

            # Poll until Carla responds or timeout
            start_time = time.time()
            while time.time() - start_time < timeout:
                if process.poll() is not None:
                    stderr = process.stderr.read().decode() if process.stderr else ""
                    logger.error("Carla exited prematurely: %s", stderr)
                    return False

                if self.is_connected():
                    logger.info(
                        "Carla started and responding (PID %d, %.1fs)",
                        process.pid,
                        time.time() - start_time,
                    )
                    return self.connect()

                time.sleep(0.5)

            logger.error("Carla failed to start within %.1fs", timeout)
            process.terminate()
            return False

        except FileNotFoundError:
            logger.error("Carla executable not found: %s", carla_cmd)
            return False
        except Exception as e:
            logger.error("Failed to start Carla: %s", e)
            return False

    def _start_listener(self) -> None:
        """Start the OSC response listener in a background thread"""
        if self._listener_thread is not None:
            return

        disp = dispatcher.Dispatcher()
        disp.set_default_handler(self._handle_response)

        try:
            self._listener_server = osc_server.ThreadingOSCUDPServer(
                (self.host, self.listen_port), disp
            )
            self._listener_thread = threading.Thread(
                target=self._listener_server.serve_forever,
                daemon=True,
                name="carla-osc-listener",
            )
            self._listener_thread.start()
            logger.debug("OSC listener started on port %d", self.listen_port)
        except OSError as e:
            logger.warning("Could not start OSC listener on port %d: %s", self.listen_port, e)

    def _stop_listener(self) -> None:
        """Stop the OSC response listener"""
        if self._listener_server is not None:
            self._listener_server.shutdown()
            self._listener_server = None
        self._listener_thread = None
        logger.debug("OSC listener stopped")

    def _handle_response(self, address: str, *args: Any) -> None:
        """Handle incoming OSC responses from Carla"""
        logger.debug("OSC received: %s %s", address, args)
        self._responses[address] = args

        # Signal any waiting threads
        event = self._response_events.pop(address, None)
        if event:
            event.set()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def __repr__(self) -> str:
        status = "connected" if self._connected else "disconnected"
        return f"CarlaOSCClient({self.host}:{self.port}, {status})"
