import threading
from typing import Tuple, Optional
import subprocess
from .logger import logger_base
logger = logger_base.get_logger(__name__)
import time


import subprocess
import time
import logging
from typing import Tuple, Optional, Dict
from fms_client.config.settings import settings_instance as settings
import serial
import re

from fms_client.device.params import device_params_instance as device_params

from .release_serial_ports import releaseSerialPorts_instance as releaseSerialPorts

class Executor:
    """
    A class to execute commands either locally or on multiple remote targets.
    """

    def __init__(self):

        self.targets: Dict[str, Dict] = {}
        self.serial_ports: Dict[str, serial.Serial] = {}
        self.serial_terminators: Dict[str, str] = {}

        self.serial_capture_flags: Dict[str, threading.Event] = {}
        self.serial_capture_threads: Dict[str, threading.Thread] = {}

        releaseSerialPorts.kill_all_ports()

        if settings:
            self._initialize_from_config(settings)

        self.SSH_OPTIONS = '-o ConnectionAttempts=20 -o StrictHostKeyChecking=no  -o UserKnownHostsFile=/dev/null'



    def _initialize_from_config(self, config: Dict):
        for name, params in config.get('ssh_targets', {}).items():
            self.add_remote(
                name,
                hostname=params.get('hostname', ''),
                username=params.get('username', 'root'),
                password=params.get('password', ''),
                port=params.get('port', 22),
                timeout=params.get('timeout', 10)
            )

        for name, params in config.get('serial_ports', {}).items():
            self.serial_add_port(
                name=name,
                port=params.get('port', ''),
                baudrate=params.get('baudrate', 115200),
                timeout=params.get('timeout', 1),
                terminator=params.get('terminator', '\n')
            )

    def add_remote(self, target_name: str, hostname: str,
                        username: str, password: str,
                        port: int = 22, timeout: int = 60) -> Tuple[bool, str]:
        if target_name in self.targets:
            logger.info(f"Credentials for '{target_name}' already initialized.")
            return False, "Already initialized"

        self.targets[target_name] = {
            "hostname": hostname,
            "username": username,
            "password": password,
            "port": port,
            "timeout": timeout
        }
        return True, f"Credentials set for {target_name}"

    def verify_ssh_connection(self, target_name: str) -> Optional[Tuple[bool, Optional[str]]]:
        try:
            success, output = self.remote(target_name, 'uptime')
            return success, output
        except Exception as ex:
            logger.error(ex)
            return False, str(ex)

    def can_ping_loop(self, target_name: str, retries=30, period=5):
        if target_name not in self.targets:
            return False, f"Unknown target: {target_name}"

        hostname = self.targets[target_name]['hostname']
        cmd = f"ping -c1 -W1 {hostname}"
        retry = 0
        while retry < retries:
            success, output = self.local(cmd)
            retry += 1
            if success:
                logger.info(f"Ping to {target_name} successful")
                return success, output
            else:
                logger.info(f"Retry {retry} to {target_name}: no response")
            time.sleep(period)
        return False, 'Device did not reply'

    def can_ping(self, target_name: str):
        if target_name not in self.targets:
            return False, f"Unknown target: {target_name}"
        hostname = self.targets[target_name]['hostname']
        cmd = f"ping -c1 -W1 {hostname}"
        success, output = self.local(cmd)
        if success:
            logger.info(f"Ping to {target_name} successful")
            return success, output
        else:
            logger.info(f"ping {target_name}: no response")
            return False, 'Device did not reply'


    def can_ssh(self, target_name: str, cmd: str = 'uptime'):
        if target_name not in self.targets:
            return False, f"Unknown target: {target_name}"
        success, output = self.remote(target_name, cmd)
        if success:
            logger.info(f"SSH {target_name} successful")
            return success, output
        else:
            logger.info(f"SSH {target_name}: no response")
            return False, 'Host did not reply'

    def can_ssh_loop(self, target_name: str, retries=30, period=5):
        retry = 0
        while retry < retries:
            success, output = self.remote(target_name, 'uptime')
            retry += 1
            if success:
                logger.info(f"SSH to {target_name} successful")
                return success, output
            else:
                logger.info(f"Retry {retry} to {target_name}: no response")
            time.sleep(period)
        return False, 'Host did not reply'

    def local(self, command) -> Tuple[bool, str]:
        logger.debug(f"Executing local command: {command}")
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"'{command}' failed: {e.stderr}")
            return False, e.stderr or e.stdout
        except Exception as e:
            logger.error(f"Command failed: {e}")
            return False, str(e)



    '''
     123456789
    *1:111    5/20 [=====>           15%                  ] FB: flash -raw2sparse all /home/pi/sbpack/images/sdcard.img*
    *1:111    5/20 [=====
    '''
    def local_stream(self, command: str, log_file: Optional[str] = None, timeout: Optional[int] = None) -> Tuple[bool, str]:
        """
        Execute a local command and stream output in real time.
        Optionally log the output to a file (like 'tee').
        """
        logger.info(f"Streaming local command: {command}")

        pattern = r"^\d{1,2}/20"

        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            assert process.stdout is not None
            log_fp = open(log_file, 'a') if log_file else None

            for line in iter(process.stdout.readline, ''):
                if "Success" in line:
                    continue
                line = line.strip()
                if len(line) > 20:
                    if line.startswith("1:111   "):
                        line = line.replace("1:111   ","")
                        line = line.strip()
                        if line.startswith('1/ 1'):
                            line = line.replace('1/ 1', '1/_1')
                            info = line.split(' ', 1)
                            info[0] = info[0].replace('/','_')
                            print(f"{info[0]} --- {info[1]}")
                        else:
                            if re.match(pattern, line):
                                info = line.split(' ', 1)
                                info[0] = info[0].replace('/','_')
                                #print(f"{info[0]} --- {info[1]}")
                    #print(f"*{line}*", end='\n')  # display to console
                    if log_fp:
                        log_fp.write(f"{line}\n")
                        log_fp.flush()

            process.stdout.close()
            returncode = process.wait(timeout=timeout)

            if log_fp:
                log_fp.close()

            if returncode == 0:
                return True, "Command completed successfully"
            else:
                return False, f"Command exited with code {returncode}"

        except subprocess.TimeoutExpired:
            process.kill()
            if log_fp:
                log_fp.close()
            return False, f"Command timed out after {timeout} seconds"
        except Exception as e:
            if log_fp:
                log_fp.close()
            return False, f"Streaming error: {e}"

    def remote(self, target_name: str, command: str, timeout: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        if target_name not in self.targets:
            return False, f"Unknown target: {target_name}"

        target = self.targets[target_name]
        hostname = target['hostname']
        username = target['username']
        password = target['password']
        timeout = timeout if timeout is not None else target['timeout']

        ssh_command = f"sshpass -p '{password}' ssh {self.SSH_OPTIONS} {username}@{hostname} \"{command}\""

        logger.debug(f"Executing remote command on {target_name}: {ssh_command}")
        if 'S95' in command:
            result = subprocess.run(
                ssh_command, shell=True, capture_output=True, text=True, check=False, timeout=timeout)
            return True, result.stdout.strip()
        else:
            try:
                result = subprocess.run(
                    ssh_command, shell=True, capture_output=True, text=True, check=True, timeout=timeout)
                return True, result.stdout.strip()
            except subprocess.TimeoutExpired:
                return False, f"Command timed out after {timeout} seconds"
            except FileNotFoundError:
                return False, "sshpass or ssh not found in PATH"
            except Exception as e:
                return False, f"{str(e)}"


    def remote_stream(self, target_name: str, command: str, log_file: Optional[str] = None, timeout: Optional[int] = None) -> Tuple[bool, str]:
        """
        Execute a remote command and stream output in real-time.
        Optionally log the output to a file (like 'tee').
        """
        if target_name not in self.targets:
            return False, f"Unknown target: {target_name}"

        target = self.targets[target_name]
        hostname = target['hostname']
        username = target['username']
        password = target['password']
        timeout = timeout if timeout is not None else target['timeout']

        ssh_command = f"sshpass -p {password} ssh {self.SSH_OPTIONS} {username}@{hostname} \"{command}\""

        logger.info(f"Streaming remote command on {target_name}: {command}")

        try:
            process = subprocess.Popen(
                ssh_command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            assert process.stdout is not None
            log_fp = open(log_file, 'a') if log_file else None
            for line in iter(process.stdout.readline, ''):
                print(line, end='')  # display to terminal
                if log_fp:
                    log_fp.write(line)
                    log_fp.flush()

            process.stdout.close()
            returncode = process.wait(timeout=timeout)

            if log_fp:
                log_fp.close()

            if returncode == 0:
                return True, "Command completed successfully"
            else:
                return False, f"Command exited with code {returncode}"
        except subprocess.TimeoutExpired:
            process.kill()
            if log_fp:
                log_fp.close()
            return False, f"Command timed out after {timeout} seconds"
        except Exception as e:
            if log_fp:
                log_fp.close()
            return False, f"Streaming error: {e}"


    def scp_transfer(self, target_name, src, dest, direction, timeout=None, recursive=False):
        if target_name not in self.targets:
            return False, f"Unknown target: {target_name}"

        target = self.targets[target_name]
        hostname = target['hostname']
        username = target['username']
        password = target['password']
        timeout = timeout if timeout is not None else target.get('timeout', 30)

        if direction not in ('upload', 'download'):
            return False, f"Invalid direction: {direction}. Must be 'upload' or 'download'."

        if direction == 'upload':
            # local src -> remote dest
            ssh_cmd = f"{username}@{hostname}:{dest}"
            cmd = f"sshpass -p '{password}' scp {self.SSH_OPTIONS} {'-r' if recursive else ''} {src} {ssh_cmd}"
        else:
            # remote src -> local dest
            ssh_cmd = f"{username}@{hostname}:{src}"
            cmd = f"sshpass -p '{password}' scp {self.SSH_OPTIONS} {'-r' if recursive else ''} {ssh_cmd} {dest}"

        try:
            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True
            )
            stdout, stderr = p.communicate(timeout=timeout)

            # Decode and log output lines, ignoring "Warning: Permanently"
            for line in stderr.decode('utf-8', errors='ignore').splitlines():
                if line.startswith('Warning: Permanently'):
                    continue
                logger.error(line)

            for line in stdout.decode('utf-8', errors='ignore').splitlines():
                if line.startswith('Warning: Permanently'):
                    continue
                logger.info(line)

            if p.returncode == 0:
                return True, None
            else:
                return False, f"SCP command failed with return code {p.returncode}"

        except subprocess.TimeoutExpired:
            p.kill()
            logger.error(f"SCP command timed out after {timeout} seconds")
            return False, f"Timeout after {timeout} seconds"
        except Exception as e:
            logger.error(f"Exception during SCP transfer: {e}")
            return False, str(e)

    def download_from_remote(self, target_name, src, dest, timeout=None, recursive=False):
        self.scp_transfer(target_name, src, dest, direction='download', timeout=timeout, recursive=recursive)

    def upload_to_remote(self, target_name, src, dest, timeout=None, recursive=False):
        self.scp_transfer(target_name, src, dest, direction='upload', timeout=timeout, recursive=recursive)

    '''
    def download_from_remote(self, target_name, src, dest, timeout=None, recursive=False):

        if target_name not in self.targets:
            return False, f"Unknown target: {target_name}"

        target = self.targets[target_name]
        hostname = target['hostname']
        username = target['username']
        password = target['password']
        #timeout = timeout if timeout is not None else target['timeout']

        ssh_cmd = f"{username}@{hostname}:{src}"
        true_cmd = f"sshpass -p '{password}' scp {self.SSH_OPTIONS} {'-r' if recursive else ''} {ssh_cmd} {dest} "
        p = subprocess.Popen(
            true_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )
        for line in iter(p.stderr.readline, b''):
            if line:
                utf8line = line.decode('utf-8').strip()
                if utf8line.startswith('Warning: Permanently'):
                    continue
                logger.error(utf8line)

        for line in iter(p.stdout.readline, b''):
            if line:
                utf8line = line.decode('utf-8').strip()
                if utf8line.startswith('Warning: Permanently'):
                    continue
                logger.info(utf8line)

        return p.wait(target['timeout']) #self.timeout)


    def upload_to_remote(self, target_name, src, dest, timeout=None, recursive=False):

        if target_name not in self.targets:
            return False, f"Unknown target: {target_name}"

        target = self.targets[target_name]
        hostname = target['hostname']
        username = target['username']
        password = target['password']
        #timeout = timeout if timeout is not None else target['timeout']

        ssh_cmd = f"{username}@{hostname}:{dest}"
        true_cmd = f"sshpass -p '{password}' scp {self.SSH_OPTIONS} {'-r' if recursive else ''} {src} {ssh_cmd}"
        p = subprocess.Popen(
            true_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )
        for line in iter(p.stderr.readline, b''):
            if line:
                utf8line = line.decode('utf-8').strip()
                if utf8line.startswith('Warning: Permanently'):
                    continue
                logger.error(utf8line)

        for line in iter(p.stdout.readline, b''):
            if line:
                utf8line = line.decode('utf-8').strip()
                if utf8line.startswith('Warning: Permanently'):
                    continue
                logger.info(utf8line)

        return p.wait(target['timeout']) #self.timeout)
    '''
    # ---------------------------------------------------------------------------------
    #
    # ---------------------------------------------------------------------------------

    def serial_add_port(self, name: str, port: str, baudrate: int = 115200,
                        timeout: float = 1.0, terminator: str = '\n') -> Tuple[bool, str]:
        #
        #
        #
        #
        #
        # if name not in self.serial_ports:
        #     if
        #     self.serial_ports[] =
        #     # msg = f"Serial port {name} not in serial port list -- Adding to serial port list"
        #     # device_params.error_message =  msg
        #     # device_params.error = True
        #     # logger.error(f"{msg}")
        #     # return False, msg

        # logger.info(f"Adding {name} / {port}")
        # if self.serial_ports[name].is_open():
        #     msg = "Serial port {name} is already open (maybe minicom). Please close it"
        #     device_params.error_message = msg
        #     device_params.error = True
        #     logger.error(f"msg")
        #     return False, msg

        try:
            ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
            self.serial_ports[name] = ser
            self.serial_terminators[name] = terminator
            msg = f"Serial port '{name}' opened on {port}"
            logger.info(msg)
            return True, msg
        except Exception as e:
            msg = f"Failed to open serial port {port}: {e}"
            device_params.error = True
            device_params.error_message = msg
            logger.error(msg)
            return False, msg

    def serial_command(self, name: str, command: str) -> Tuple[bool, Optional[str]]:
        try:
            self.serial_write_to(name, command)
            time.sleep(0.100)
            return self.serial_read_from(name)
        except Exception as ex:
            logger.error(f'Serial command: {command}')
            return False

    def serial_write_to(self, name: str, data: str) -> Tuple[bool, str]:
        if name not in self.serial_ports:
            return False, f"Serial port '{name}' not found"

        terminator = self.serial_terminators.get(name, '\n')
        try:
            self.serial_ports[name].write((data + terminator).encode())
            return True, f"Data written to '{name}'"
        except Exception as e:
            return False, f"Write failed on '{name}': {e}"

    def serial_read_from(self, name: str, size: int = 1024) -> Tuple[bool, str]:
        if name not in self.serial_ports:
            return False, f"Serial port '{name}' not found"
        try:
            data = self.serial_ports[name].read(size).decode(errors='replace')
            return True, data
        except Exception as e:
            return False, f"Read failed on '{name}': {e}"

    def serial_close_all_ports(self):
        for name, ser in self.serial_ports.items():
            try:
                ser.close()
            except Exception:
                pass
        self.serial_ports.clear()
        self.serial_terminators.clear()

    def serial_start_capture(self, name: str, output_file: str) -> Tuple[bool, str]:
        if name not in self.serial_ports:
            return False, f"Serial port '{name}' not found"

        if name in self.serial_capture_threads and self.serial_capture_threads[name].is_alive():
            return False, f"Capture already running on '{name}'"

        stop_event = threading.Event()
        self.serial_capture_flags[name] = stop_event

        def capture():
            with open(output_file, 'w') as f:
                logger.info(f"Started capturing serial output from '{name}' to '{output_file}'")
                while not stop_event.is_set():
                    try:
                        line = self.serial_ports[name].readline().decode(errors='replace')
                        if line:
                            if line.startswith('I2P2'):
                                info = line.strip().split('IOTX')
                                device_params.device_id = info[1]
                            f.write(f"{line}")
                            f.flush()
                    except Exception as e:
                        logger.error(f"Error while reading from '{name}': {e}")
                        exit(0)
                logger.info(f"Stopped capturing serial output from '{name}'")

        thread = threading.Thread(target=capture, daemon=True)
        self.serial_capture_threads[name] = thread
        thread.start()
        msg = f"Started capture on '{name}'"
        logger.debug(msg)
        return True, msg

    def serial_stop_capture(self, name: str) -> Tuple[bool, str]:
        if name not in self.serial_capture_flags:
            return False, f"No capture session found for '{name}'"

        self.serial_capture_flags[name].set()
        self.serial_capture_threads[name].join(timeout=5)
        msg = f"Stopped capture on '{name}'"
        logger.debug(msg)
        return True, msg


executor_instance = Executor()
