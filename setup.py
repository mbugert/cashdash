from setuptools import find_packages, setup

setup(
    name="cashdash",
    version="0.0.1",
    author="Michael Bugert",
    description="Interactive visualization of GnuCash data based on plotly Dash.",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.7",
    install_requires=["flask",],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Programming Language :: Python :: 3.7",
        "Topic :: Office/Business :: Financial :: Accounting",
    ],
)
