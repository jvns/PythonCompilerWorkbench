Python Compiler Workbench
=========================

This is a live coding environment to help you develop intuitions about how
Python source code compiles to ASTs and bytecodes.

Watch the [1.5-minute YouTube demo](https://www.youtube.com/watch?v=fMCV3KNYquo).


## Installing

1. [Download GraphViz](http://www.graphviz.org/Download..php) and install it.
2. Install two Python packages: `bottle` and `pydot`.

One way to install is:

    easy_install pip
    pip install bottle
    pip install pydot


## Running

1. Run `python backend.py` to start the server.
2. Visit http://localhost:8080/index.html

(tested with Python 2.7 on Mac OS X so far)
