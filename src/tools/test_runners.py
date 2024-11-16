""" Holds the test runners for test suites in different programming languages. """
import os
import shutil
import subprocess
import logging

LOGGER = logging.getLogger("TestRunner")


def node_js_test_runner(sample_project_path) -> tuple[bool, str]:
    """ Run the test cases for a Node.js project. """
    bash_cmd = [f'cd {sample_project_path} && npm run test']
    with subprocess.Popen(
        bash_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    ) as process:
        command, result = process.communicate()

    command = command.decode('utf-8')
    result = result.decode('utf-8')

    if result.startswith("PASS"):
        LOGGER.info("Tests passed.")
        return True, "Tests passed. Code may be committed."

    LOGGER.warning("Tests failed. Output: %s", result)
    return False, result

def python_test_runner(sample_project_path) -> tuple[bool, str]:
    """ Run the test cases for a Python project. """

    # sed command is used to remove the color codes from the pytest output
    bash_cmd = [f"cd {sample_project_path} && pytest | sed -e 's/\x1b\[[0-9;]*m//g'"] # pylint: disable=anomalous-backslash-in-string
    with subprocess.Popen(
        bash_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    ) as process:
        command, _ = process.communicate()

    command = command.decode("utf-8")

    lines = command.splitlines()
    lines = [line for line in lines if line]

    result_line = lines[-1]
    erroneous_lines = [line for line in lines if line.startswith(("FAILED", "ERROR"))]

    if len(erroneous_lines) > 0:
        return False, result_line + "\n".join(erroneous_lines)
    return True, "Tests passed. Code may be committed."

def java_test_runner(sample_project_path) -> tuple[bool, str]:
    """ Compile and run the test cases for a Java project. """
    def parse_mvn_output(output_string: str) -> tuple[bool, str]:
        parsed_command = output_string.split("\n")

        if any("[INFO] BUILD SUCCESS" in s for s in parsed_command):
            return True, "[INFO] SUCCESS"

        error_lines = [s for s in parsed_command if s.startswith("[ERROR]")]
        if len(error_lines) > 0:
            return False, "\n".join(error_lines)
        return False, "[ERROR] FAILURE"

    # clean the build directory
    build_dir = os.path.join(sample_project_path, "target")
    try:
        shutil.rmtree(build_dir)
    except OSError as e:
        # the target directory might not exist yet
        LOGGER.warning("Error: %s - %s.", e.filename, e.strerror)

    # compile the code
    bash_cmd = [f'cd {sample_project_path} && mvn compile']
    with subprocess.Popen(
        bash_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    ) as process:
        command, _ = process.communicate()

    compilation_output = command.decode("utf-8")

    # verify the compilation
    compilation_success, detail = parse_mvn_output(compilation_output)
    if not compilation_success:
        return False, f"Compilation Error: {detail}"

    # exec unit tests
    bash_cmd = [f'cd {sample_project_path} && mvn test']
    with subprocess.Popen(
        bash_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    ) as process:
        command, _ = process.communicate()

    test_output = command.decode("utf-8")
    test_success, detail = parse_mvn_output(test_output)
    if not test_success:
        return False, detail

    # comilation and test successfull
    return True, "[INFO] COMPILATION & TEST SUCCESS"
