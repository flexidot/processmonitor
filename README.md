# What does it do?

This is a Simple tool for monitoring processes, checking their memory usage and restarting them if needed. Restarts can happen if the process is using too much memory (and later on more metrics) or if it is not running.

processmonitor will also log all the processes, their pids, time started, and CPU and memory usage, so you can do a time series of the process.

The tool is written in python and is designed to be installed and used very easily.

## How should I run this?
At the least *processmonitor* needs a config file.
If *processmonitor* is run by itself, without any command line options and without a config file, it will go through all the running processes an log basic information about them on the console and then the tools exists.

The most common usecase is to run *processmonitor* with a config file. The install comes with a sample config file that you can copy to **config.json** to get started rightaway.

The default configuration will log everything that the tool does into a log file. It also creates a SQL Lite database file where all processes' information is logged.

## What platforms are supported or tested?
Testing on ubuntu 14.04. The core program is written in Python 3.

## How is configuration managed?
All configuration is managed in a json file. The default name of the config file is config.json. A sample json file is included with the distribution.

# Mail Integration
Right now only supports sendgrid, though no reason why any other SMTP can't be easily supported

# Why is this useful? Or why did you create it?
This was created to monitor docker images that Flexidot runs for their customers. We did not find an easy way to monitor systems, images and processes so we created this for ourselves. Of course, we made  this open source, as a way to thank the open source community.

# Plan for the future
High level roadmap
* add command line support for all options
* add flask support to create a local web server so process information can be managed via a web browser
* Allow *processmonitor* to act as an agent to report stats and control to a remote server

# What is Flexidot
Flexidot gives you your very own online marketing officer for your small and medium business. Now you can attract new customers, engage them through nurture campaigns, and convert them to paying customers. It requires very little effort on your part. Flexidot provides end to end tools for digital marketing automation. Our software is fully integrated, simple, intuitive and easy to use. We can help you to collect leads, run campaigns and measure their effectiveness so that you can get the best results for your investment.

* Collect Leads through online forms
* Engage customers using marketing campaigns
* Grow revenue by scaling marketing and converting visitors to paying customers

# How does Flexidot use this ?
Flexidot uses a lot of systems and docker images for its system. We use this system for all our hosts, and docker images.

# Why did Flexidot make this open source?
Flexidot uses a lot of open source components for our own use. This is our way of giving back to the open source community, to whom we are very thankful.

# What is the license?

# How can I credit you?
If you use this tool, please point to our github page.

# Where all is this used?
https://www.flexidot.com
http://www.innovatorsandleaders.com
