from setuptools import setup, find_packages
setup(
    name = "VYSOS",
    version = "1.1.2",
    author='Josh Walawender',
    packages = find_packages(),
#     entry_points = {
#         'console_scripts': [
#             'measureimage = scripts.measure_image:main',
#             'measurenight = scripts.measure_night:main',
#             'monitor = scripts.watch_directory:main',
#             'makenightlyplots = scripts.make_nightly_plots:main',
#             'cleanupIQMon = scripts.remove_old_plots:main',
#             'copydatalocal = data_handling.copy_data_local:main',
#             'copydataremote = data_handling.copy_data_remote:main',
#         ]}
)
