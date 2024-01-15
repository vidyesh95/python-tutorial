# Data Types
"""
# Strings(str)
# Numerical types(int, float, complex)
# Sequence types(list, tuple, range)
# Mapping type(dict)
# Set types(set, frozenset)
# Boolean type(bool)
# Binary types(bytes, bytearray, memoryview)
# Printing types(type())
"""
# Getting the Data Type
"""
You can get the data type of any object by using the type() function:
"""
# Example
month = "February"
print(type(month))

# int type
binary = 0b1010
print(binary, "is of type", type(binary))
octal = 0o310
print(octal, "is of type", type(octal))
hexadecimal = 0x12c
print(hexadecimal, "is of type", type(hexadecimal))

# float type
float_num = 10.51324243242354546567423434
print(float_num, "is of type", type(float_num))

# complex type
real = 5
imaginary = 3
complex_num = complex(real, imaginary)
print("Complex number is",complex_num,'of type',type(complex_num))

# Sequence types
# list
list1 = [1, 2, 3, 4, 5]
print(list1, "is of type", type(list1))
# tuple
tuple1 = (1, 2, 3, 4, 5)
print(tuple1, "is of type", type(tuple1))
# range
range1 = range(10)
print(range1, "is of type", type(range1))

# Mapping type
# dict
dict1 = {1: 'one', 2: 'two', 3: 'three'}
print(dict1, "is of type", type(dict1))

# Set types
# set
set1 = {1, 2, 3, 4, 5}
print(set1, "is of type", type(set1))
# frozenset
frozenset1 = frozenset({1, 2, 3, 4, 5})
print(frozenset1, "is of type", type(frozenset1))

# Boolean type
# bool
bool1 = True
print(bool1, "is of type", type(bool1))

# Binary types
# bytes
bytes1 = b'Hello'
print(bytes1, "is of type", type(bytes1))
# bytearray
bytearray1 = bytearray(5)
print(bytearray1, "is of type", type(bytearray1))
# memoryview
memoryview1 = memoryview(bytes1)
print(memoryview1, "is of type", type(memoryview1))

# Setting the Specific Data Type
"""
If you want to specify the data type, you can use the following constructor functions:
"""
# Example
x = str("Hello World")  # str
y = int(20)  # int
z = float(20.5)  # float
print(x, "is of type", type(x))
print(y, "is of type", type(y))
print(z, "is of type", type(z))

# Random Number
"""
Python does not have a random() function to make a random number, but Python has a built-in module called random that
can be used to make random numbers:
"""
# Example
import random
print(random.randrange(1, 10))

# Casting
"""
Specify a Variable Type
There may be times when you want to specify a type on to a variable. This can be done with casting. Python is an
object-orientated language, and as such it uses classes to define data types, including its primitive types.
Casting in python is therefore done using constructor functions:
"""
# Example
x = str(3)  # x will be '3'
y = int(3)  # y will be 3
z = float(3)  # z will be 3.0
print(x, "is of type", type(x))
print(y, "is of type", type(y))
print(z, "is of type", type(z))

# Python Strings
"""
Strings in python are surrounded by either single quotation marks, or double quotation marks.
'hello' is the same as "hello".
"""
# Example
print("Hello")
print('Hello')

# Assign String to a Variable
"""
Assigning a string to a variable is done with the variable name followed by an equal sign and the string:
"""
# Example
a = "Hello"
print(a)

# Multiline Strings
"""
You can assign a multiline string to a variable by using three quotes:
"""
# Example
a = """Lorem ipsum dolor sit amet,
consectetur adipiscing elit,
sed do eiusmod tempor incididunt
ut labore et dolore magna aliqua."""
print(a)

# Strings are Arrays
"""
Like many other popular programming languages, strings in Python are arrays of bytes representing unicode characters.
However, Python does not have a character data type, a single character is simply a string with a length of 1.
Square brackets can be used to access elements of the string.
"""
# Example
a = "Hello, World!"
print(a[1])

val = None
print(val)