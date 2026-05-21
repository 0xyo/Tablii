@echo off
echo ========================================
echo   Compiling Tablii PFE Report (LaTeX)
echo ========================================
echo.

cd /d "%~dp0"

echo Step 1: Running pdflatex (1st pass)...
pdflatex -interaction=nonstopmode main.tex
echo.

echo Step 2: Running pdflatex (2nd pass - TOC/refs)...
pdflatex -interaction=nonstopmode main.tex
echo.

echo Step 3: Running pdflatex (3rd pass - final)...
pdflatex -interaction=nonstopmode main.tex
echo.

if exist main.pdf (
    echo ========================================
    echo   SUCCESS: rapport_pfe_tablii.pdf created
    echo ========================================
    echo.
    echo Opening PDF...
    start main.pdf
) else (
    echo ========================================
    echo   ERROR: Compilation failed
    echo   Check main.log for details
    echo ========================================
)

pause
