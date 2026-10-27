# Bioman Bio-Culture React site

This is a Vite + React frontend based on the supplied Bio-Culture HTML/JavaScript and the current website's visual reference.

## Run locally

```sh
npm install
npm run dev
```

## Build

```sh
npm run build
npm run preview
```

The production bundle is written to `dist/`. Checkout posts `customer_name`, `phone`, `address`, `city`, `state`, `pincode`, `pack`, and `amount` to the new same-origin Frappe method `create_bioculture_order_react`. The support form continues to use `create_support_issue`. The frontend contains no ERP or Razorpay credentials. Serve the page from the Frappe origin so session authentication and same-origin requests work. Do not submit live orders while testing.

The supplied Python Server Script was not copied into or modified by this React project.
