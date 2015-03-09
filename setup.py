from setuptools import setup, find_packages
setup(
    name = "VYSOS",
    version = "1.0",
    author='Josh Walawender',
    packages = find_packages(),
    entry_points = {
        'console_scripts': [
            'measureimage = scripts.MeasureImage:main',
            'measurenight = scripts.MeasureNight:main',
            'monitor = scripts.Monitor:main',
            'makenightlyplots = scripts.MakeNightlyPlots:main',
            'makewebpage = scripts.MakeWebPage:main',
            'cleanupIQMon = scripts.CleanUpIQMon:main',
        ]}
)
