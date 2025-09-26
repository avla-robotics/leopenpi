from draccus import parse
from so101_pi.utils.runtime_configuration import RuntimeConfiguration

def main(config: RuntimeConfiguration):
    print(config)


if __name__ == "__main__":
    config = parse(RuntimeConfiguration)
    main(config)