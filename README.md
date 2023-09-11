# jbang-python - Java Script in your Python

Install and use [JBang](https://www.jbang.dev) from Python-based projects.

![](python_jbang.png)

Lets you use your own local scripts, [JBang AppStore](https://jbang.dev/appstore) alias or any network reachable jar or Maven artifact.

## Usage
The `jbang.exec()` function accepts a string that will be passed as the command-line arguments to the `jbang` executable.

Given this script `test.py`:

```python
#! /usr/bin/env python
import jbang
jbang.exec('properties@jbangdev')
```

Now you can invoke the `test` script from the command-line:

```
python test.py
```

You can easily pass command-line arguments around:

```python
import sys
args = ' '.join(sys.argv1:])
jbang.exec('com.myco.mylib:RELEASE ' + args)
```

So now if you run `python test.py arg1 arg2`, `arg1 arg2` will be appended to the command executed.

## Behind the scenes

When you run `pip install` - JBang and other dependencies will be installed. This uses the [`app setup`](https://www.jbang.dev/documentation/guide/latest/installation.html#using-jbang) command.

Opening a new terminal or shell may be required to be able to use the `jbang` command from the system `PATH`.

## Similar projects

* [jgo](https://pypi.org/project/jgo/) - allows execution of Maven artifacts by using Maven.

