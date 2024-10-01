import os, logging, sys

from dotenv import load_dotenv
load_dotenv()

from agent import CodeRefactoringAgent

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.info("Application started.")

    # the application that we want to refactor is passed as an command line argument
    if len(sys.argv) < 3:
        logger.error("Usage: python main.py <repository_to_refactor> <relative_dir_to_refactor>")
        sys.exit(1)

    project = os.path.abspath(sys.argv[1])
    directory = sys.argv[2]
    refact = CodeRefactoringAgent(project, directory)
    refact.run()
