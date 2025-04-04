#!/usr/bin/python3

import xml.etree.ElementTree as ET
import base64
import json
import sys
import os

def parse_http_request_response(base64_encoded_data):
    """
    Parses a base64-encoded raw HTTP request or response and returns a JSON object
    containing the headers and the re-encoded body/content.

    Args:
        base64_encoded_data: The base64-encoded HTTP request or response string.

    Returns:
        A tuple containing a JSON string of headers and the re-encoded body/content,
        or (None, None) if an error occurs.
    """
    try:
        decoded_data = base64.b64decode(base64_encoded_data).decode('utf-8')
        lines = decoded_data.splitlines()
        headers = {}
        body_content = ""
        header_parsing_complete = False

        for line in lines[1:]:  # Skip the first line (request/status line)
            if not line.strip():  # Empty line signals end of headers
                header_parsing_complete = True
                continue

            if not header_parsing_complete:
                if ": " in line:
                    key, value = line.split(": ", 1)
                    headers[key] = value
            else:
                body_content += line + "\n"

        if body_content:
            body_content = base64.b64encode(body_content.rstrip('\n').encode('utf-8')).decode('utf-8')

        return headers, body_content

    except (base64.binascii.Error, UnicodeDecodeError, ValueError) as e:
        return None, None # or return f"Error: {e}" for more verbose error reporting.

def xml_file_to_json(xml_file_path):
    """
    Converts an XML file to a JSON string.

    Args:
        xml_file_path: The path to the XML file.

    Returns:
        A JSON string representing the XML data, or an error message.
    """
    if not os.path.exists(xml_file_path):
        return f"Error: File not found at '{xml_file_path}'"

    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        items = []

        for item_element in root.findall('item'):
            item = {}
            for child in item_element:
                text = child.text if child.text is not None else ""
                if child.tag == 'request':
                    headers, body = parse_http_request_response(text)
                    item[child.tag] = {'value': body, 'base64': child.get('base64', 'false')}
                    item['request_headers'] = headers
                elif child.tag == 'response':
                    headers, content = parse_http_request_response(text)
                    item[child.tag] = {'value': content, 'base64': child.get('base64', 'false')}
                    item['response_headers'] = headers
                elif child.tag == 'host':
                    item[child.tag] = {'value': text, 'ip': child.get('ip', '')}
                else:
                    item[child.tag] = text

            items.append(item)

        result = {
            'items': items,
            'burpVersion': root.get('burpVersion', ''),
            'exportTime': root.get('exportTime', '')
        }

        return json.dumps(result, indent=4)

    except ET.ParseError as e:
        return f"Error parsing XML: {e}"
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python xml_to_json.py <xml_file_path>")
        sys.exit(1)

    xml_file_path = sys.argv[1]
    json_output = xml_file_to_json(xml_file_path)
    print(json_output)
