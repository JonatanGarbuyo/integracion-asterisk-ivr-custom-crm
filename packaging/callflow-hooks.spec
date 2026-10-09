Name:           issabel-callflow-hooks
Version:        %{cfh_version}
Release:        %{cfh_release}
Summary:        Extensible IVR handlers with native Issabel administration
License:        GPLv3+
URL:            https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/tree/%{cfh_commit}
Source0:        callflow-hooks-%{version}.tar.gz
BuildArch:      noarch
AutoReqProv:    no
Requires:       issabel-framework >= 4.0.0
Requires:       issabelPBX >= 2.11.0
Requires:       python3 >= 3.6
Requires:       php >= 5.4
Requires(pre):  /usr/bin/python3
Requires(post): /usr/bin/python3
Requires(preun): /usr/bin/python3

%description
Native Issabel menu and ACL, schema-based profile forms, an IssabelPBX
destination/dialplan bridge and a local JSON/AGI runtime. Configuration is
preserved across upgrades and removal. Source commit: %{cfh_commit}.

%prep
%setup -q -n callflow-hooks-%{version}

%build

%install
mkdir -p %{buildroot}/var/www/html/modules/callflowhooks
mkdir -p %{buildroot}/var/www/html/admin/modules/callflowhooks
mkdir -p %{buildroot}/usr/share/callflow-hooks
mkdir -p %{buildroot}/usr/sbin
install -m 755 packaging/callflow-hooksctl %{buildroot}/usr/sbin/callflow-hooksctl
cp -a native/. %{buildroot}/var/www/html/modules/callflowhooks/
cp module/*.php module/module.xml %{buildroot}/var/www/html/admin/modules/callflowhooks/
cp -a module/backend module/extensions %{buildroot}/usr/share/callflow-hooks/
cp native/menu.xml packaging/pbx-state.php packaging/lifecycle.py version.json %{buildroot}/usr/share/callflow-hooks/
chmod 755 %{buildroot}/usr/share/callflow-hooks/backend/entry.py
find %{buildroot}/var/www/html -type f -exec chmod 644 {} \;
mkdir -p %{buildroot}/var/lib/callflow-hooks

%pre
# Check services/dependencies before replacing code on an existing PBX.
/usr/bin/python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,6) else 1)' || exit 1

%post
/usr/bin/python3 /usr/share/callflow-hooks/lifecycle.py install || exit 1

%preun
if [ "$1" = 0 ]; then
    /usr/bin/python3 /usr/share/callflow-hooks/lifecycle.py remove || exit 1
fi

%files
%defattr(-,root,root,-)
/var/www/html/modules/callflowhooks
/var/www/html/admin/modules/callflowhooks
/usr/share/callflow-hooks
/usr/sbin/callflow-hooksctl
%attr(700,root,root) %dir /var/lib/callflow-hooks

%changelog
* Thu Oct 08 2026 CallFlow Hooks contributors - 0.2.4-1
- Verify the configured Asterisk daemon PID without confusing remote consoles.

* Thu Oct 08 2026 CallFlow Hooks contributors - 0.2.3-1
- Keep native PBX navigation inside Issabel and clarify IVR destination selection.

* Thu Oct 08 2026 CallFlow Hooks contributors - 0.2.2-1
- Preserve nonsecret failed form drafts and show safe field and access errors.

* Thu Oct 08 2026 CallFlow Hooks contributors - 0.2.1-1
- Compare effective service UIDs and preserve safe preflight diagnostics.

* Thu Oct 08 2026 CallFlow Hooks contributors - 0.2.0-1
- Native Issabel administration, shared runtime and direct repository installer.
