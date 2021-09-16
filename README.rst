=====================
RealTimeCommunication
=====================


.. image:: https://img.shields.io/pypi/v/rtcom.svg
        :target: https://pypi.python.org/pypi/rtcom

.. image:: https://img.shields.io/github/workflow/status/rjean/rtcom/Upload%20Python%20Package
        :target: https://github.com/rjean/rtcom/actions?query=workflow%3A%22Upload+Python+Package%22

.. image:: https://readthedocs.org/projects/rtcom/badge/?version=latest
        :target: https://rtcom.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status




Real Time Communication Library for home robotics and automation. 

The aim of this library is to provide a quick and easy way to prototype "Intranet of Things" devices. 

It was first developed for a hobby robotics project in order to have a interface between the robot and a PC,
without having to worry about networking, IP addresses, hostnames, web servers or callbacks. 

* Free software: MIT license
* Documentation: https://rtcom.readthedocs.io.

Features
--------

* Real-time UDP broadcast based synchronisation of all rtcom nodes.
* Automatic discovery of devices. (No DNS or Avahi required)
* Possibility of unicast, without having to worry about IP addresses, DNS or Avahi.
* Get started with just a few lines of code.

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
