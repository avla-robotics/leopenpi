from draccus import parse
from so101_pi.utils.environment_configuration import EnvironmentConfiguration

def main(environment_configuration: EnvironmentConfiguration):
    print(environment_configuration)


if __name__ == "__main__":
    config = parse(EnvironmentConfiguration)
    main(config)