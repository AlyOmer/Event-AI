#!/bin/bash
# Validate all Event-AI Claude Code skills

echo "🔍 Validating skills in $(pwd)/skills/"

SKILLS_DIR="$(dirname "$0")"
INVALID=0
VALID=0

for file in "$SKILLS_DIR"/*.prompt.md; do
    if [ ! -f "$file" ]; then
        echo "⚠️  No .prompt.md files found"
        exit 0
    fi

    echo "Checking: $(basename "$file")"

    # Check YAML frontmatter starts with ---
    if ! head -n1 "$file" | grep -q "^---$"; then
        echo "  ❌ Missing frontmatter delimiter at start"
        INVALID=$((INVALID+1))
        continue
    fi

    # Check closing --- exists
    if ! grep -q "^---$" "$file"; then
        echo "  ❌ Missing closing frontmatter delimiter"
        INVALID=$((INVALID+1))
        continue
    fi

    # Extract YAML frontmatter only (between first two --- markers)
    YAML=$(sed -n '1,/^---$/p' "$file" | sed '1d;$d')

    # Check required fields
    REQUIRED_FIELDS=("name" "description" "version" "invocation")
    for field in "${REQUIRED_FIELDS[@]}"; do
        if ! echo "$YAML" | grep -q "^$field:"; then
            echo "  ❌ Missing required field: $field"
            INVALID=$((INVALID+1))
            continue 2
        fi
    done

    # Check invocation.command present
    if ! echo "$YAML" | grep -A5 "^invocation:" | grep -q "command:"; then
        echo "  ❌ Missing invocation.command"
        INVALID=$((INVALID+1))
        continue
    fi

    # Check system_prompt exists in skill content (after second ---)
    AFTER_YAML=$(sed -n '/^---$/,$p' "$file" | tail -n +2)
    if ! echo "$AFTER_YAML" | grep -q "system_prompt:"; then
        echo "  ⚠️  Missing system_prompt section"
    fi

    # Check user_message_template exists
    if ! echo "$AFTER_YAML" | grep -q "user_message_template:"; then
        echo "  ⚠️  Missing user_message_template section"
    fi

    # Check output_format exists
    if ! echo "$AFTER_YAML" | grep -q "output_format:"; then
        echo "  ⚠️  Missing output_format section"
    fi

    echo "  ✅ Valid structure"
    VALID=$((VALID+1))
done

echo ""
echo "📊 Summary: $VALID valid, $INVALID invalid"
echo ""

if [ $INVALID -eq 0 ]; then
    echo "✅ All skills are properly structured!"
    exit 0
else
    echo "❌ Some skills need fixes"
    exit 1
fi
