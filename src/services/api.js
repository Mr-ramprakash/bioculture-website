const getCsrfToken = () => (window.frappe ? window.frappe.csrf_token : "");

async function postFrappeMethod(method, values) {
  const body = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => body.append(key, value));

  const response = await fetch(`/api/method/${method}`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "X-Frappe-CSRF-Token": getCsrfToken(),
    },
    body: body.toString(),
  });

  const responseText = await response.text();
  let data;

  try {
    data = responseText ? JSON.parse(responseText) : null;
  } catch {
    data = null;
  }

  if (data === null) {
    const isLocalPreview = ["localhost", "127.0.0.1"].includes(
      window.location.hostname,
    );
    if (isLocalPreview) {
      throw new Error(
        "The Frappe API is not available in the local preview. Open the page on your ERPNext/Frappe website to create the Sales Order and Razorpay payment link.",
      );
    }
    throw new Error(
      `Frappe method "${method}" returned an empty or non-JSON response (HTTP ${response.status}).`,
    );
  }

  if (!response.ok) {
    const message =
      typeof data.message === "string"
        ? data.message
        : `Frappe request failed (HTTP ${response.status}).`;
    throw new Error(message);
  }

  return data;
}

export function createBioCultureOrder(values) {
  return postFrappeMethod("create_bioculture_order", values);
}
export function createSupportIssue(values) {
  return postFrappeMethod("create_support_issue", values);
}
