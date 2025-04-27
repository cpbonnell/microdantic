# Microdantic

Microdantic is a pure python library that is intended to be a replacement for
Pydantic that is compatible with MicroPython / CircuitPython, and usable on
embedded devices.

## Why Microdantic?

Pydantic is a wonderful library for data validation, serialization, and
deserialization. It is heavily used in the software industry for ensuring that
parties communicating over the internet can agree on and enforce data contracts.

Even though the library is extremely fast, it is too large to be included on
small devices (like Arduino), and makes use of some metaprogramming features not
available on MicroPython or CircuitPython. So it is not suitable as a tool for
enforcing data contracts over IoT networks such as BlueTooth or USB connections.

Enter Microdantic! Microdantic is intended to be a relatively small library
written in a style of Python compatible with MicroPython, CircuitPython, and
CPython. It replicates much of the core functionality and syntax of Pydantic in
a form that is deployable with Python projects running on small microcontroller
devices.

Using Microdantic, developers can write data models to be shared between a fleet
of microcontrollers, a Python gateway app running on a RaspberryPi, and AWS
Lambda functions running in the cloud, confident that the contract will be
interpreted identically on all parts of the distributed application.

Microdantic is thoroughly tested, and all checks are run on both a CPython
running on an x86 processor, as well as CircuitPython running on an Arduino.

## How this documentation is organized

A high level overview of the sections in this document is useful for quickly
finding the information that is relevant to your needs. The main sections of the
documentation (in order) are:

* **Tutorials** - A quick set of steps to accomplish a specific common task.
  Using a tutorial requires little or no prior knowledge of `microdantic` or
  `pydantic`.
* **How-To Guides** - These guides are recipes for using specific parts of
  `microdantic`'s functionality. They guide you through the trade-offs and
  decisions you will need to make, and also how to apply the various features to
  solve specific problems. They require some prior knowledge of
  `microdantic`, and will often compare and contrast how the same thing is
  commonly accomplished in `pydantic`.
* **Topic Guides** - These sections discuss key concepts at a fairly high level,
  and provide useful information about `microdantic`'s implementation.
* **Reference Guide** - Complete documentation of all `microdantic`'s classes
  and functions can be found in the docstrings of those entities.

# Tutorials

## 1. Define your data contract using a model

The magic of Microdantic all starts with the `BaseModel` class. Any class that
inherits from `BaseModel` will get all the magic functionality included
automatically. Such child classes are generically referred to as **models**.
Then you may declare a set of **fields** that belong to that model. For example,
let's say that we want a model to represent a point in 2-dimensional space, and
we want the default value for both components to be
"0.0". The following code shows how we might define that model and create
several instances of it:

```python
from microdantic import BaseModel


class Point2D(BaseModel):
    x = 0.0
    y = 0.0


# Any field not specified gets the default value
origin = Point2D()
unit_x = Point2D(x=1.0)
unit_y = Point2D(y=1.0)

# The order of parameters doesn't matter
point_a = Point2D(x=5.0, y=-2.0)
point_b = Point2D(y=-2.0, x=5.0)

# Models can be compared
point_a == point_b  # True
point_a == origin  # False

# The value of a field can be changed later on
point_b.y = 10.0
point_a == point_b  # False
```

As you can see, once you define your model by specifying the field names and
defaults, you can create instances by specifying the values you want in any
order to the constructor. Any values you don't specify will be assigned the
default value.

What to read next:

* [Tutorial 2: Constraining field values](#-2-constraining-field-values)

## 2. Constraining field values

Sometimes you may want to restrict the possible values that a field may take.
For example, say that we wanted to use the `Point2D` model from Tutorial 1, but
we wanted to ensure that the point is always in the first quadrant (i.e. the
values of both `x` and `y` are always positive).

Microdantic provides the class `Field` that we can use when defining our fields.
Among other things, the `Field` class allows us to enforce constraints on the
data. If anyone tries to assign a value to that field that violates our
constraint, then Microdantic will raise an error clearly listing what data
constraint the value failed to meet. The following code snippet illustrates
this:

```python
from microdantic import BaseModel, Field


class Point2D(BaseModel):
    x = Field(float, default=0.0, ge=0.0)
    y = Field(float, default=0.0, ge=0.0)


point_a = Point2D()

point_a.x = 3.0  # This will work

point_a.x = -3.0  # This will raise an error

# ValidationError: The following validations failed when attempting to assign 
# the value '-3.0' to field 'x':
# -- Value must be greater than 0.0
```

Since we know that the data contract is enforced at runtime while the data is
being constructed, we can write our code safe in the knowledge that if someone
else sends us a `Point2D` over the network, then that `Point2D` will be
well-behaved and follow the rules we expect it to.

What to read next:

* [Topic Guide: Field Validation]()

## 3. Sending data
Microdantic provides a simple way to serialize your data into a format that can
be sent over the network. Most IoT communication channels require your data 
to be sent in a binary encoding. The BaseModel class provides a method that 
writes out your entire object (a.k.a. "serializes") in JSON format and 
encodes it in a byte array. The following code snippet shows an example of 
sending a `Point2D` object over a USB connection from an Arduino device using 
CircuitPython: 
```Python
# CircuitPython running on an Arduino device
import usb_cdc
from microdantic import BaseModel, Field

class Point2D(BaseModel):
    x = Field(float, default=0.0, ge=0.0)
    y = Field(float, default=0.0, ge=0.0)
    
point_a = Point2D(x=3.0, y=4.0)

usb_cdc.data.write(point_a.model_dump_jsonb())

```

Whatever device the arduino is connected to will be able to read the data 
from the serial port on the other side and reconstruct the original 
`Point2D` object from that data:

```Python
# CPython running a host device
import serial
from microdantic import BaseModel, Field

class Point2D(BaseModel):
  x = Field(float, default=0.0, ge=0.0)
  y = Field(float, default=0.0, ge=0.0)


serial_name = '/dev/ttyUSB0'  # Change this to the name of your serial port
serial_instance = serial.Serial(serial_name, baudrate=115200)

for line in serial_instance.readlines():
    # Read the data from the serial port
    point_a = Point2D.model_validate_jsonb(line)
    print(point_a)
```