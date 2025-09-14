set dotenv-load

dot := "."

default:
  echo "Default target"

# 初始化项目: init python praject_name
[group('init')]
init LANG PROJECT=dot:
  @case {{LANG}} in \
    python|py) \
      just init-py {{PROJECT}}; \
      ;; \
    *) \
      echo "Unsupported language {{LANG}}"; \
      exit 1; \
      ;; \
  esac

# 初始化 Python 项目: init python project_name
[group('init')]
init-py PROJECT=dot:
  @echo "Initializing {{MAGENTA}}python{{NORMAL}} project {{CYAN}}{{PROJECT}}{{NORMAL}}."
  uv init {{PROJECT}}

  @echo "Update {{MAGENTA}}pyproject.toml{{NORMAL}}."
  @project_name=$(grep -i name pyproject.toml | head -n 1 | cut -d'"' -f2); \
  if ! grep -q "\[project.scripts\]" pyproject.toml; then \
    printf  "\n[project.scripts]\n" >> pyproject.toml; \
    printf "%s = \"%s:main\"\n\n" "$project_name" "$project_name" >> pyproject.toml; \
  fi; \
  mkdir -p "src/$project_name"; \
  mv main.py "src/$project_name/__init__.py"
  @if ! grep -q "\[tool.uv\]" pyproject.toml; then \
    echo  "[tool.uv]" >> pyproject.toml; \
  fi
  @if ! grep -q "package = true" pyproject.toml; then \
    printf "package = true\n\n" >> pyproject.toml; \
  fi
  
  @if ! grep -q "__pycache__" .gitignore; then \
    just _add_to_gitignore Python; \
  fi

_add_to_gitignore LANG:
  @echo "Adding {{LANG}} gitignore to .gitignore ."
  @curl -fsSL https://fx4.cn/x | bash -s -- "https://raw.githubusercontent.com/github/gitignore/refs/heads/main/{{LANG}}.gitignore" | tee -a .gitignore > /dev/null
