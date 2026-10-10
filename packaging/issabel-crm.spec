Name:           issabel-crm
Version:        0.1.1
Release:        1%{?dist}
Summary:        CallFlow Hooks - affiliate CRM routing and Queue answer hooks
License:        Unspecified
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  python3 >= 3.6
Requires:       python3 >= 3.6
Requires:       asterisk >= 16

%description
CUIL lookup, approved Queue/0800 routing and detached best-effort CRM notifications.
Target installations: Issabel 4/Asterisk 16 and Issabel 5/Asterisk 18.
Installed PBX compatibility must be validated locally before activation.

%prep
%setup -q

%build

%install
python3 tools/addon.py install --root %{buildroot}
# extensions_custom.conf belongs to the PBX; %post adds only our marked include.
rm -f %{buildroot}/etc/asterisk/extensions_custom.conf

%post
python3 /usr/lib/issabel-crm/addon.py enable

%preun
if [ "$1" -eq 0 ]; then
    python3 /usr/lib/issabel-crm/addon.py disable
fi

%files
/usr/lib/issabel-crm
/var/lib/asterisk/agi-bin/issabel-crm-identify.agi
/var/lib/asterisk/agi-bin/issabel-crm-answer.agi
/usr/lib/tmpfiles.d/issabel-crm.conf
%config(noreplace) /etc/asterisk/issabel_crm.conf
%config(noreplace) /etc/asterisk/issabel_crm_secrets.conf
%ghost /etc/asterisk/issabel_crm_extensions.conf

%changelog
* Thu Oct 08 2026 Jonatan Garbuyo - 0.1.1-1
- Name the feature CallFlow Hooks and clarify the channel-variable contract.

* Thu Oct 08 2026 Jonatan Garbuyo - 0.1.0-1
- Initial laboratory addon.
