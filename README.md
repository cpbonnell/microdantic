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
finding the information that is relevant to your needs. The main sections of 
the documentation (in order) are:

* **Tutorials** - A quick set of steps to accomplish a specific common task. 
  Using a tutorial requires little or no prior knowledge of `microdantic` or 
  `pydantic`.
* **How-To Guides** - These guides are recipes for using specific parts of 
  `microdantic`'s functionality. They guide you through the trade-offs and 
  decisions you will need to make, and how to apply the various features to 
  solve specific problems. They require some prior knowledge of 
  `microdantic`, and will often compare and contrast how the same thing is 
  commonly accomplished in `pydantic`.
* **Topic Guides** - These sections discuss key concepts at a fairly high 
  level, and provide useful information about `microdantic`'s implementation.
* **Reference Guide** - Complete documentation of all `microdantic`'s classes 
  and functions can be found in the docstrings of those entities.