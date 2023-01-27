echo Running ISort...
isort .
echo

echo Running Black...
black --line-length 120 --extend-exclude postgres_data .
echo

echo Running Flake8...
flake8 --exclude ./venv .
echo