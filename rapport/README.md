# Rapport PFE - Tablii (LaTeX)

## Comment compiler

### Option 1: Script Windows
Double-cliquez sur `compile.bat`

### Option 2: Manuellement
```bash
cd rapport
pdflatex main.tex
pdflatex main.tex
pdflatex main.tex
```

### Option 3: Avec latexmk
```bash
latexmk -pdf main.tex
```

## Prerequis
- TeX Live ou MiKTeX installe
- Packages requis: `tikz`, `fontawesome5`, `listings`, `tabularx`, `booktabs`, `fancyhdr`, `titlesec`, `tocloft`, `colortbl`, `babel` (french), `xcolor`, `geometry`, `hyperref`

## Output
Le fichier PDF sera genere a: `rapport/main.pdf`
