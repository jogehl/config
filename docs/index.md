# Welcome to Simple Config Builder

This is a simple tool to help you build a configuration file for your project.

## Installation

```bash
pip install simple_config_builder
```

## Getting Started
When writing your library configuration files are often a necessity. 
Instead of using a dictionary or a class to store your configuration,
you can build config classes using this tool.

```python
from simple_config_builder.config import configclass
from simple_config_builder.config import config_field

@configclass
class MyConfig:
    name: str = "John Doe"
    age: int = 30
    is_student: bool = False
    grades: int = config_field(gt=0, lt=100)
```

This will create a class with the specified fields and default values and validation rules.

For IO, you can use 
```python
from simple_config_builder.configparser import Configparser
from simple_config_builder.config import configclass
from simple_config_builder.config import config_field

@configclass
class MyConfig:
    name: str = "John Doe"
    age: int = 30
    is_student: bool = False
    grades: int = config_field(gt=0, lt=100, default=90)

# Load and parse the configuration file
config = Configparser("config.json")

# Save the configuration file
config.save()

# reload the configuration file
config.reload()

# Set a config object
config['my_config'] = MyConfig("John Doe", 30, False, 90)
```

Apart from that autosave and autoreload is supported. 

## License
This project is licensed under the MIT License - see the [LICENSE](license.md) file for details.