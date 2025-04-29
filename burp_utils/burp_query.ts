import { JSONFilePreset } from 'lowdb/node'

type Item = {
    time: string; // Example: "Wed Apr 16 04:54:46 CDT 2025"
    url: string;  // Example: "https://xxx.xxx.xxx/asdf/foo/bar"
    host: {
        value: string; // Example: "xxx.xxx.xxx"
        ip: string;    // Example: "xxx.xx.xxx.x"
    };
    port: string;     // Example: "443"
    protocol: string; // Example: "https"
    method: string;   // Example: "POST"
    path: string;     // Example: "/asdf/foo/bar"
    extension: string; // Note: The example value is the string "null", not the null type.
    request: {
        value: string; // Base64 encoded or empty string
        base64: string; // Example: "true" (as a string)
    };
    request_headers: Record<string, string>; // Object containing request headers
    status: string;         // Example: "200" (as a string)
    responselength: string; // Example: "1088" (as a string)
    mimetype: string;       // Example: ""
    response: {
        value: string; // Base64 encoded or empty string
        base64: string; // Example: "true" (as a string)
    };
    response_headers: Record<string, string>; // Object containing response headers
    comment: string;        // Example: ""
}

type Data = { items : Item[] }

const defaultData: Data = {
    items: []
}

const db = await JSONFilePreset('out.json', defaultData)

const { items } = db.data;

// find requests where the Host header is reflected in the response
//const host_reflected_in_response = await items.filter((item) => item.request_headers && atob(item.response.value).includes(item.request_headers['Host']))

// find requests where a piece of the path is reflected in the response
// const path_reflected_in_response = await items.filter(function (item) {
//     const data = atob(item.response.value);

//     let found = item.path.split('/').slice(-2).reduce((a, c) => a || data.includes(c), false)

//     return found;
// })

// find requests where Host header == ACAO Header

const possibly_reflected_cors_origin = await items.filter((i: Item) => {
    return i?.response_headers?.['Access-Control-Allow-Origin'] && i?.response_headers?.['Access-Control-Allow-Origin'].includes(i?.request_headers?.['Host'])
}, false)

console.log(possibly_reflected_cors_origin)