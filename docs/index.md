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

### Callables
You can also use callables as fields in the config class. 
```python
from simple_config_builder.config import configclass
from simple_config_builder.config import config_field
from typing import Callable

@configclass
class MyConfig:
    name: str = "John Doe"
    age: int = 30
    is_student: bool = False
    grades: int = config_field(gt=0, lt=100, default=90)
    student_name_calling: Callable
```
The callables are saved in the configuration files as package.module
name and function name. If the module is not in the python path,
a file_path is saved additionally.

```json
{
    "name": "John Doe",
    "age": 30,
    "is_student": false,
    "grades": 90,
    "student_name_calling": 
    {
      "module": "package.module",
      "function": "function_name",
      "file_path": "path/to/file"
    }
}
```


### Typing
A decorated class is of type Configclass so that type hints can be used.

```python
from simple_config_builder.config import configclass, Configclass
from simple_config_builder.config import config_field


@configclass
class MyConfig:
    name: str = "John Doe"
    age: int = 30
    is_student: bool = False
    grades: int = config_field(gt=0, lt=100)

    
c = MyConfig(
    name="John Doe",
    age=30,
    is_student=False,
    grades=90
)    

c.name = "Jane Doe"

def my_function(config: Configclass):
    print(config.name)

my_function(MyConfig())

```



## Documentation
For good documentation a mkdocstrings extension is provided as 
a python package which can be installed using pip.

```bash
pip install mkdocstrings-extensions-simple-config-builder
```

This extension should be added to the list of extensions 
in the mkdocstrings section of your mkdocs.yml file.

```yaml
mkdocstrings:
  handlers:
    python:
        options:
            extensions:
              - mkdocstrings_extensions_simple_config_builder
```
It will generate documentation for the config classes and fields.
It is avaible at: 
[Extension Plugin](https://github.com/jogehl/mkdocstrings-extensions-simple-config-builder) 

## License
This project is licensed under the MIT License - see the [LICENSE](license.md) file for details.