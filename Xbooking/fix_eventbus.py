#!/usr/bin/env python
"""
Script to fix all EventBus.publish() calls to use Event objects
"""
import re
import sys
from pathlib import Path

def fix_eventbus_calls(filepath, source_module):
    """Fix EventBus.publish calls in a file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already fixed
    if "event = Event(" in content and "EventBus.publish(event)" in content:
        print(f"✓ {filepath} - Already fixed")
        return False
    
    # Add Event import if not present
    if 'from core.services import EventBus, Event' not in content:
        content = content.replace(
            'from core.services import EventBus',
            'from core.services import EventBus, Event'
        )
    
    # Pattern to match EventBus.publish('EVENT', { ... })
    # This is complex due to nested braces, so we'll do it line by line
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this line starts an EventBus.publish call with old format
        if "EventBus.publish('" in line and not "event = Event(" in lines[max(0, i-5):i]:
            # Extract event name
            match = re.search(r"EventBus\.publish\('([^']+)',\s*\{", line)
            if match:
                event_name = match.group(1)
                indent = len(line) - len(line.lstrip())
                
                # Find the end of the data dict
                brace_count = 1
                data_lines = [line.split('{', 1)[1]]  # Get part after first {
                j = i + 1
                
                while j < len(lines) and brace_count > 0:
                    data_lines.append(lines[j])
                    brace_count += lines[j].count('{') - lines[j].count('}')
                    j += 1
                
                # Remove closing })
                data_content = '\n'.join(data_lines)
                if data_content.rstrip().endswith('})'):
                    data_content = data_content.rstrip()[:-2]  # Remove })
                elif data_content.rstrip().endswith('}'):
                    data_content = data_content.rstrip()[:-1]  # Remove }
                
                # Create new Event-based code
                fixed_lines.append(f"{' ' * indent}event = Event(")
                fixed_lines.append(f"{' ' * indent}    event_type='{event_name}',")
                fixed_lines.append(f"{' ' * indent}    data={{")
                fixed_lines.append(data_content)
                fixed_lines.append(f"{' ' * indent}    }},")
                fixed_lines.append(f"{' ' * indent}    source_module='{source_module}'")
                fixed_lines.append(f"{' ' * indent}})")
                fixed_lines.append(f"{' ' * indent}EventBus.publish(event)")
                
                i = j
                continue
        
        fixed_lines.append(line)
        i += 1
    
    # Write back
    fixed_content = '\n'.join(fixed_lines)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print(f"✓ Fixed {filepath}")
    return True

def main():
    base_path = Path(__file__).parent
    
    files_to_fix = [
        ('payment/services/__init__.py', 'payment'),
        ('payment/webhooks/v1/handlers.py', 'payment'),
        ('payment/webhooks/v1/views.py', 'payment'),
    ]
    
    fixed_count = 0
    for filepath, source_module in files_to_fix:
        full_path = base_path / filepath
        if full_path.exists():
            if fix_eventbus_calls(full_path, source_module):
                fixed_count += 1
        else:
            print(f"✗ {filepath} not found")
    
    print(f"\n{'='*50}")
    print(f"Fixed {fixed_count} file(s)")
    print(f"{'='*50}")

if __name__ == '__main__':
    main()
