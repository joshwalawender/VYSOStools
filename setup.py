from setuptools import setup, find_packages
setup(
    name = "VYSOS",
    version = "1.1.2",
    author='Josh Walawender',
    packages = find_packages(),
    entry_points = {
        'console_scripts': [
            'makeweatherplot = VYSOS.make_plots:main',
            'copydatalocal = data_handling.copy_data:main',
            'printcdatadir = VYSOS.cdata:main'
        ]}
)
