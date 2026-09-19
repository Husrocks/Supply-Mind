# Contributing to SupplyMind

First off, thank you for considering contributing to SupplyMind! 🎉 

SupplyMind is an ambitious project combining Agentic AI with robust Supply Chain management, and we rely on the open-source community to make it better. Whether you're fixing a bug, improving the machine learning models, creating new features, or writing documentation, your help is greatly appreciated!

---

## 🛠 Setting up your Development Environment

To start contributing, you need to set up a local development environment.

1. **Fork the Repository:** Click the "Fork" button at the top right of this page to create your own copy of the repository.
2. **Clone your Fork:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/supplymind.git
   cd supplymind
   ```
3. **Set up a Virtual Environment:** We require Python 3.10+.
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Mac/Linux:
   source .venv/bin/activate
   ```
4. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   # Alternatively, if you're working heavily on the backend you might want to install test tools directly:
   pip install pytest pytest-asyncio pytest-cov ruff mypy
   ```

---

## 🧑‍💻 Coding Standards & Conventions

We maintain a strict code quality standard to ensure reliability and maintainability. This project uses `pyproject.toml` to configure its tools.

- **Linting & Formatting:** We use `ruff` as our primary linter and formatter.
  - Line length is set to 100 characters.
  - Before committing, ensure your code passes linting:
    ```bash
    ruff check .
    ```
- **Type Checking:** We use `mypy` for static type checking. We highly encourage the use of Python type hints (`typing` module) in all new backend code.
  - Run type checks via:
    ```bash
    mypy .
    ```
- **Docstrings:** Please document your functions, classes, and complex logic blocks clearly.

---

## 🧪 Testing

We use `pytest` for our unit and integration tests.

- All new features and bug fixes **must** include corresponding tests.
- Run the test suite before submitting a Pull Request:
  ```bash
  pytest
  ```
- To view test coverage:
  ```bash
  pytest --cov=. --cov-report=term-missing
  ```
  Ensure that your additions do not drastically reduce the overall test coverage. (See `[tool.coverage.run]` in `pyproject.toml` for omitted paths).

---

## 🚀 Branching & Pull Request Workflow

1. **Create a new branch:** Always create a new branch from `main` for your work. Name it descriptively (e.g., `feature/add-new-ml-model`, `bugfix/fix-ui-crash`, `docs/update-readme`).
   ```bash
   git checkout -b your-branch-name
   ```
2. **Make your changes:** Follow the coding and testing standards outlined above.
3. **Commit your changes:** Write clear and concise commit messages. 
   ```bash
   git commit -m "Add short, descriptive commit message"
   ```
4. **Push to your fork:**
   ```bash
   git push origin your-branch-name
   ```
5. **Submit a Pull Request (PR):**
   - Go to the original SupplyMind repository.
   - Click "Compare & pull request".
   - Fill out the PR template clearly explaining what changes you made, why you made them, and how they can be tested.
   - Wait for a maintainer to review your code. We may request some changes before it can be merged.

---

## 🐛 Found a Bug or Have a Feature Request?

If you find a bug or have an idea for a new feature but aren't ready to write the code yourself, please open an Issue!

- **For bugs:** Include steps to reproduce, expected behavior, actual behavior, and details about your environment (OS, Python version).
- **For features:** Explain why the feature is needed and how it would improve the project.

---

## 💬 Community & Code of Conduct

By participating in this project, you are expected to uphold a welcoming, inclusive, and professional environment. Please be respectful and constructive in all discussions, reviews, and issues.

Thank you for contributing to SupplyMind!
