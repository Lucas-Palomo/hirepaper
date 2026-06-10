\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{standard}[2026/05/30 CurriculumGen Standard Layout]

\LoadClass[10pt, letterpaper]{article}

% ----- geometry -----
\RequirePackage[top=0.3in, bottom=0.25in, left=0.40in, right=0.40in]{geometry}

% ----- fonts (LuaLaTeX + fontspec) -----
\RequirePackage{fontspec}
\setmainfont{DejaVu Sans}

% ----- colors -----
\RequirePackage{xcolor}
\definecolor{accentcolor}{HTML}{1a6b8a}
\definecolor{headingcolor}{HTML}{1a2b3c}
\definecolor{subdued}{HTML}{7a8a9a}
\definecolor{linkcolor}{HTML}{1a6b8a}

% ----- packages -----
\RequirePackage[colorlinks=true, urlcolor=linkcolor]{hyperref}
\RequirePackage{enumitem}
\RequirePackage{titlesec}
\RequirePackage{array}
\RequirePackage{graphicx}
\RequirePackage[none]{hyphenat}
\RequirePackage{needspace}

% ----- page style -----
\pagestyle{empty}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.5pt}
\setlength{\emergencystretch}{0.5em}

% ----- section formatting (12pt bold accent, thin rule) -----
\titleformat{\section}
  {\fontsize{12}{14}\selectfont\bfseries\color{accentcolor}}
  {}{0em}{}[\vspace{-1pt}\color{accentcolor!30!white}\titlerule\vspace{5pt}]
\titlespacing{\section}{0pt}{6pt}{1pt}

% ----- itemize (flush left, label embedded in item text) -----
\setlist[itemize]{
  leftmargin=0pt,
  labelindent=0pt,
  itemindent=0pt,
  labelwidth=0pt,
  topsep=0.5pt,
  itemsep=0.3pt,
  parsep=0pt,
  label={},
  before={\fontsize{9.5}{11.5}\selectfont},
}

% ----- commands -----

% --- Header ---
\newcommand{\resumeName}[1]{%
  {\centering\fontsize{16}{19}\selectfont\bfseries\color{headingcolor}#1\par}%
}

\newcommand{\resumeHeadline}[1]{%
  {\centering\fontsize{11}{14}\selectfont\color{subdued}#1\par}%
  {\color{accentcolor!50!white}\rule{\textwidth}{0.5pt}}\vspace{3pt}\par%
}

\newcommand{\resumeContact}[1]{%
  {\centering\fontsize{9.5}{11.5}\selectfont #1\par}\vspace{1pt}\par%
}

\newcommand{\resumeLinks}[1]{%
  {\raggedright\fontsize{9.5}{11.5}\selectfont #1\par}\vspace{1pt}\par%
}

% --- Sections (with page-break protection) ---
\newcommand{\resumeSection}[1]{%
  \nopagebreak[3]%
  \needspace{1.5\baselineskip}%
  \section{#1}%
  \nopagebreak[3]%
}

% --- Compact section heading for use inside two-column band ---
\newcommand{\resumeBandSection}[1]{%
  \needspace{2\baselineskip}%
  {\fontsize{11}{14}\selectfont\bfseries\color{accentcolor}#1\par}%
  \vspace{2pt}%
}

% --- Entry (experience, education, volunteer) ---
\newcommand{\resumeEntry}[4]{%
  \noindent
  \begin{tabular}{@{}>{\raggedright\arraybackslash}p{0.68\textwidth}@{}>{\raggedleft\arraybackslash}p{0.32\textwidth}@{}}
    \normalsize\bfseries{#1} & \normalsize\bfseries{#2} \\[-6pt]
    {\fontsize{9.5}{11.5}\selectfont\color{subdued} #4} & {\fontsize{9.5}{11.5}\selectfont\color{subdued} #3} \\
  \end{tabular}\vspace{5pt}\nobreak\par%
}

% --- Sub-line (role context, supporting text) ---
\newcommand{\resumeEntrySub}[1]{%
  {\fontsize{9.5}{11.5}\selectfont #1}\vspace{0.5pt}\par%
}

% --- Technology/keyword line (smaller secondary text, placed after bullets) ---
\newcommand{\resumeTechSub}[1]{%
  {\fontsize{8.5}{10.5}\selectfont\color{subdued} #1}\vspace{1pt}\par%
}

% --- Icons (decorative SVGs) ---
\newcommand{\iconEmail}{\raisebox{-0.08em}{\includegraphics[height=0.7em]{envelope.pdf}}}
\newcommand{\iconPhone}{\raisebox{-0.08em}{\includegraphics[height=0.7em]{phone.pdf}}}
\newcommand{\iconPin}{\raisebox{-0.08em}{\includegraphics[height=0.7em]{pin.pdf}}}
\newcommand{\iconLink}{\raisebox{-0.08em}{\includegraphics[height=0.65em]{link.pdf}}}

% --- Separator between entries ---
\newcommand{\resumeEntrySep}{%
  \vspace{2pt}%
  {\centering\normalsize\normalcolor\color{subdued!35!white}\makebox[0.5\linewidth]{\xleaders\hbox{- \ }\hfill}\par}%
  \vspace{2pt}%
}

% --- Rule between major sections (matches headline style) ---
\newcommand{\resumeSectionRule}{%
  \vspace{3pt}%
  {\centering\normalcolor\color{accentcolor!50!white}\rule{\textwidth}{0.5pt}\par}%
  \vspace{4pt}%
}

% --- Bullets (flush left, consistent item spacing) ---
\newcommand{\resumeHighlights}[1]{%
  \begin{itemize}
    #1%
  \end{itemize}%
}

% --- Skills (compact inline) ---
\newcommand{\resumeSkillCategory}[2]{%
  \noindent
  {\fontsize{9.5}{11.5}\selectfont\textbf{#1:}} #2\vspace{0.5pt}\par%
}

% --- Awards (compact one-line) ---
\newcommand{\resumeAward}[3]{%
  \noindent
  \fontsize{9.5}{11.5}\selectfont\textbf{#1} --- #2\hfill #3\vspace{0.5pt}\par%
}

% --- Certifications (two-line entry) ---
\newcommand{\resumeCertification}[3]{%
  \noindent
  {\fontsize{9.5}{11.5}\selectfont\textbf{#1}\par}%
  {\fontsize{9.5}{11.5}\selectfont #2 --- #3\vspace{3pt}\par}%
}

% --- Volunteer ---
\newcommand{\resumeVolunteer}[4]{%
  \noindent
  \begin{tabular}{@{}>{\raggedright\arraybackslash}p{0.68\textwidth}@{}>{\raggedleft\arraybackslash}p{0.32\textwidth}@{}}
    \normalsize\bfseries{#1} & \normalsize\bfseries{#2} \\[-6pt]
    {\fontsize{9.5}{11.5}\selectfont\color{subdued} #4} & {\fontsize{9.5}{11.5}\selectfont\color{subdued} #3} \\
  \end{tabular}\vspace{5pt}\nobreak\par%
}

% --- Languages (soft utility) ---
\newcommand{\resumeLanguage}[2]{%
  \noindent
  {\fontsize{9.5}{11.5}\selectfont #1:} #2\par%
}

% --- Compact section heading for use inside two-column band ---
\newcommand{\resumeBandSection}[1]{%
  {\fontsize{11}{14}\selectfont\bfseries\color{accentcolor}#1\par}%
  \vspace{3pt}%
}

\endinput
