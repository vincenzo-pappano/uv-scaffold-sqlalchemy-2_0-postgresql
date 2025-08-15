from typing import Tuple
import random

from ..utils.logger import logger_base
logger = logger_base.get_logger(__name__)

from ..utils.executor import executor_instance as executor


class Passwords():

    special_chars = '@_!#%^*()&<>?}{~'
    min_length = 8
    max_length = 16  # the diceware component should be max_length-3 (we will prepend or append a random number between 1 and 998 - inclusive )

    def __init__(self) -> None:
        pass

    def generate_all(self, root_password=None) -> Tuple[bool, dict]:
        config = {}

        if not root_password:
            config['root_password'] = self.generate()
        else:
            config['root_password'] = root_password
        logger.info(f"root.password={config['root_password']}")
        _, config['root_hash'] = self.generate_hash('root.hash', config['root_password'])

        config['admin_password'] = self.generate()
        logger.info(f"admin.password={config['admin_password']}")
        _, config['admin_hash'] = self.generate_hash('admin.hash', config['admin_password'])

        config['ineez_admin_password'] = self.generate()
        logger.info(f"ineez_admin.password={config['ineez_admin_password']}")
        _, config['ineez_admin_hash'] = self.generate_hash('ineez_admin.hash', config['ineez_admin_password'])

        config['ineez_user_password'] = self.generate()
        logger.info(f"ineez_user.password={config['ineez_user_password']}")
        _, config['ineez_user_hash'] = self.generate_hash('ineez_user.hash', config['ineez_user_password'])

        config['wlan0_ap_password'] = self.generate()

        return (True, config)


    def generate(self, password = None) -> str:
        if password is None or len(password) == 0:
            random.seed()
            v = random.randrange(0,2)
            if v == 0:
                return self.generate_password_dice() + str(self.generate_password_randint())
            else:
                return str(self.generate_password_randint()) + self.generate_password_dice()
        else:
            return password

    def generate_password_dice(self) -> str:
        password = 'Invalid'
        is_valid = False
        while not is_valid:
            _, password = executor.local("diceware -n 2 -c -s 1")
            (is_valid, error) = self.__verify_dice_password(password)
        return password.strip()

    def generate_password_randint(self, limit=999) -> int:
        number = 0
        is_valid = False
        random.seed()
        while not is_valid:
            number = random.randrange(1,limit)
            if number < 10:
                is_valid = True
            elif number < 100:
                digit1 = number // 10
                digit2 = number % 10
                if digit2 == digit1 + 1:
                    continue
                if digit2 == digit1 - 1:
                    continue
                break
            else:
                digit1 = number // 100
                digit2 = (number % 100) // 10
                digit3 = ((number % 100) % 10)
                if digit3 == digit2 + 1 and digit2 == digit1 + 1:
                    continue
                if digit3 == digit2 - 1 and digit2 == digit1 - 1:
                    continue
                break
        return number

    def __verify_dice_password(self, password) -> Tuple[bool, str]:
        success = True
        error = None
        if len(password) < self.min_length:
            success = False
            error = 'At least ' + str(self.min_length) + ' characters required'
        if len(password) > (self.max_length - 3):
            success = False
            error = 'No more than ' + str(self.max_length - 3) + ' characters allowed'
        if not any(c.islower() for c in password):
            success = False
            error =  'At least one lowercase'
        if not any(c.isupper() for c in password):
            success = False
            error = 'At least one uppercase'
        if not any(c in self.special_chars for c in password):
            success = False
            error = 'At least one special character needed'
        return (success, error)

    def generate_hash(self, msg: str, password: str) -> Tuple[bool, str]:
        cmd = f"openssl passwd -6 -salt $(openssl rand -base64 9) '{password}'"
        success, output = executor.local(cmd)
        logger.info(f"Computing hash for {msg} - success: {success}")
        logger.info(output)
        if not success:
            logger.error('Could not create root password hash - Exiting')
            return (False, None)
        return (True, output.strip())

passwords_instance = Passwords()


if __name__ == '__main__':
    passwords = Passwords()
    #tool.create_initial_config()
