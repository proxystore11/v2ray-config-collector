# در فایل GitHub Actions workflow
name: Auto Update PRX11

on:
  schedule:
    - cron: '0 */6 * * *'  # هر ۶ ساعت
  workflow_dispatch:

jobs:
  update-configs:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
      with:
        token: ${{ secrets.GITHUB_TOKEN }}
        fetch-depth: 0  # دریافت تاریخچه کامل

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Run PRX11 Collector
      run: python main.py

    - name: Configure Git
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"

    - name: Pull latest changes
      run: |
        git pull origin main --rebase

    - name: Commit and push changes
      run: |
        git add .
        git commit -m "🤖 Auto-update PRX11: $(date +'%Y-%m-%d %H:%M')"
        git push origin main
