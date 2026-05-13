1. xesmf cannot be installed though pip. One has to install one of its dependencies - esmpy using mamba


2. is the following structure of postprocessing acceptable:
   - the forecast and hindcast files are picked up based on a standard naming convention and the user-provided information, so the user provides a directory where data are stored and a forecast date
an alternative is as follows:
   - user provides path to hindcast and forecast files, and forecast date is inferred from file names or time variable
 
3. the worked example notebooks. At the moment - I've added a jupyter notebook to /testing directory, but...

worked examples can be built into the readthedocs using an automated setup. That setup would also automatically create API from docstrings. 

The thing I came across is sphinx https://www.sphinx-doc.org/en/master/
implementing it allows for two things:
- autogeneration of api entries based on docstrings for each of the public functions
- autogeneration of example jupyter notebooks included in readthedocs if these are placed in docs/examples
and these integrate automatically with contents written "by hand"
NB. this is a library that you install on your computer - it does not have any implication to the package

4. Include jupyter lab in the package?

5. do we want to include sample data - including observations (which might be bulky) in the package? I set up download of example files from the csag server. Can we build them into the package? or keep the function to download data from an external source? is there an alternative to the csag server?
