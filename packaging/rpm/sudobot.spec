Name:           sudobot
Version:        0.1.2
Release:        1%{?dist}
Summary:        Lightweight, fast, offline-first CLI typo correction utility
License:        MIT
URL:            https://github.com/sudobot/sudobot
Source0:        %{name}-%{version}.tar.gz
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-wheel
BuildRequires:  python3-rapidfuzz

%description
SudoBot provides automatic typo correction for command-line interfaces.
When you mistype a command, SudoBot suggests the intended command and
asks for confirmation before executing it. Uses fuzzy matching with
conservative confidence thresholds. Supports Bash and PowerShell.

%prep
%setup -q

%build
python3 -m build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_datadir}/sudobot/integrations
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_pythonpath}

# Install Python package
python3 -m pip install --no-deps --target %{buildroot}%{_pythonpath} dist/sudobot-0.1.2-py3-none-any.whl

# Create wrapper script for the CLI
cat > %{buildroot}%{_bindir}/sudobot << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '%{_pythonpath}')
from sudobot.cli import main
sys.exit(main())
EOF
chmod 755 %{buildroot}%{_bindir}/sudobot

# Install shell integration scripts
install -m 644 src/sudobot/integrations/bash.sh %{buildroot}%{_datadir}/sudobot/integrations/bash.sh
install -m 644 src/sudobot/integrations/powershell.ps1 %{buildroot}%{_datadir}/sudobot/integrations/powershell.ps1

%files
%{_bindir}/sudobot
%{_datadir}/sudobot/
%{_pythonpath}/sudobot/
%{_pythonpath}/sudobot-0.1.2.dist-info/

%changelog
* Sun Sep 21 2026 SudoBot Contributors <sudobot@example.com> - 0.1.2-1
- Fix PowerShell command-not-found interception via lookup action
* Sun Sep 21 2026 SudoBot Contributors <sudobot@example.com> - 0.1.1-1
- Fix Windows standalone PowerShell installer profile resolution
* Mon Sep 20 2026 SudoBot Contributors <sudobot@example.com> - 0.1.0-1
- Initial package
