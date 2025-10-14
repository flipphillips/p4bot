Local secrets for development — NOT for committing.

Place your Perforce ticket and optional p4config here for local dev testing.

Examples (on host):

mkdir -p secrets

# copy ticket from host ~/.p4tickets

cp ~/.p4tickets secrets/p4tickets

# or create a p4config file with P4PORT/P4USER

cat > secrets/p4config <<EOF
P4PORT=ssl:mss-perforce-01.rit.edu:1666
P4USER=p4status
P4TICKETS=/root/.p4tickets
EOF

The `secrets` directory is git-ignored by the repository's `.gitignore` (patterns covering `**/secrets/*`).
