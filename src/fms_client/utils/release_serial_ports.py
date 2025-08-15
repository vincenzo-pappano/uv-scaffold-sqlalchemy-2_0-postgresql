import subprocess
import os
import signal
import time

from .logger import logger_base
logger = logger_base.get_logger(__name__)

class ReleaseSerialPorts:
    # List of ports to manage (change as needed)
    ports = ['/dev/ttyACM0', '/dev/ttyNumato', '/dev/ttyAMA0']

    def __init__(self, port_name=None):
        self.port_name = port_name

    def find_pids_using_port(self, port_name=None):
        port = port_name or self.port_name
        if not port:
            raise ValueError("Port name must be specified")

        ps_cmd = ['ps', '-eo', 'pid,args']
        pids = set()

        try:
            ps_output = subprocess.check_output(ps_cmd, text=True).splitlines()
        except Exception as e:
            logger.error(f"Failed to run ps: {e}")
            return []

        for line in ps_output[1:]:
            parts = line.strip().split(None, 1)
            if len(parts) < 2:
                continue
            pid, cmdline = parts
            if port in cmdline:
                pids.add(int(pid))

        try:
            lsof_output = subprocess.check_output(['lsof', port], text=True).splitlines()
            for line in lsof_output[1:]:
                fields = line.split()
                if len(fields) >= 2:
                    pid = int(fields[1])
                    pids.add(pid)
        except subprocess.CalledProcessError:
            pass
        except Exception as e:
            logger.error(f"Failed to run lsof: {e}")

        return sorted(pids)

    def kill_processes(self, pids, port_name=None, timeout=3):
        port = port_name or self.port_name or "unknown port"
        for pid in pids:
            try:
                logger.info(f"Terminating PID {pid} (port {port})")
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                logger.error(f"PID {pid} does not exist")
            except PermissionError:
                logger.error(f"Permission denied killing PID {pid}")
            except Exception as e:
                logger.error(f"Error killing PID {pid}: {e}")

        if timeout > 0:
            time.sleep(timeout)
            for pid in pids:
                if self._is_process_alive(pid):
                    try:
                        logger.info(f"Force killing PID {pid} (port {port})")
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    except PermissionError:
                        logger.error(f"Permission denied force killing PID {pid}")
                    except Exception as e:
                        logger.error(f"Error force killing PID {pid}: {e}")

    def _is_process_alive(self, pid):
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True

    def kill_all_ports(self):
        for port in self.ports:
            pids = self.find_pids_using_port(port)
            if pids:
                logger.info(f"Found processes using {port}: {pids}")
                self.kill_processes(pids, port)
            else:
                logger.info(f"No processes found using {port}")


# Example usage
# if __name__ == "__main__":
#     manager = ReleaseSerialPorts()
#     manager.kill_all_ports()

releaseSerialPorts_instance = ReleaseSerialPorts()
