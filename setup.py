from setuptools import setup, find_packages
setup(
    name = "VYSOS",
    version = "1.0",
    author='Josh Walawender',
    packages = find_packages(),
    entry_points = {
        'console_scripts': [
            'measureimage = MeasureImage:main',
            'measurenight = MeasureNight:main',
            'monitor = Monitor:main',
            'makenightlyplots = MakeNightlyPlots:main',
            'makewebpage = MakeWebPage:main',
            'cleanupIQMon = CleanUpIQMon:main',
        ]}
)
