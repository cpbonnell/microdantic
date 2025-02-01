"""
This is a test suite for microdantic.

It is done as a regular Python script rather than using a testing framework
because the tests need to be easily run on a microcontroller running
MicroPython as well as on a regular computer running CPython.

Embedded Python implementations like Circuit Python often automatically run
a file named main.py when the device is powered on. This makes it easy to
run the tests on a device by simply copying this file together with
microdantic.py to the device. The tests can be run on the host machine by
running `poetry run tests` inside the project directory.
"""

from microdantic import Field, BaseModel


def test_one():
    print("...inside test_one")


def test_two():
    print("...inside test_two")


def run_tests():
    print("==================== Beginning Test Suite ====================")
    tests_to_run = {
        name: obj for name, obj in globals().items() if name.startswith("test_")
    }

    for name, executable in tests_to_run.items():
        if not callable(executable):
            print(f"Symbol {name} is not callable. Skipping execution.")

        print(f"===== Running {name} =====")
        executable()


if __name__ == "__main__":
    run_tests()
