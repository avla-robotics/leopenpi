from dataclasses import dataclass

@dataclass(frozen=True)
class EnvironmentConfiguration:
    prompt: str
    cameras: dict[str, int]
    robot_port: int
    server_ip: str
    server_port: int = 8000
    max_steps: int = 1000
    log_level: str = "INFO"


