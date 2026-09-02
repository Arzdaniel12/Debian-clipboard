#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
version=$(sed -n 's/^version = "\([^"]*\)"/\1/p' "$project_dir/pyproject.toml")
package_dir="$project_dir/dist/clipboard-history_${version}_all"
output="$project_dir/dist/clipboard-history_${version}_all.deb"

rm -rf "$package_dir" "$output"
mkdir -p "$package_dir/DEBIAN" "$package_dir/usr/lib/clipboard-history" \
    "$package_dir/usr/bin" "$package_dir/usr/share/applications"

cp "$project_dir/debian/control" "$package_dir/DEBIAN/control"
cp -r "$project_dir/clipboard_history" "$package_dir/usr/lib/clipboard-history/"
find "$package_dir/usr/lib/clipboard-history" -type d -name __pycache__ -prune -exec rm -rf {} +
cp "$project_dir/clipboard-history.desktop" "$package_dir/usr/share/applications/"
cat > "$package_dir/usr/bin/clipboard-history" <<'EOF'
#!/bin/sh
export PYTHONPATH="/usr/lib/clipboard-history${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m clipboard_history "$@"
EOF
chmod 755 "$package_dir/usr/bin/clipboard-history"

dpkg-deb --build --root-owner-group "$package_dir" "$output"
rm -rf "$package_dir"
printf 'Created %s\n' "$output"