// app/static/dashboard.js

let chartTopCustomers = null;
let chartPieCustomers = null;
let chartTopSalesmen = null;
let chartTopItems = null;
let chartSalesmanCompare = null;
let chartItemCompare = null;

function formatRupiah(n) {
    if (n == null) return "Rp 0";
    return "Rp " + n.toLocaleString("id-ID", { maximumFractionDigits: 2 });
}

async function loadDashboard() {
    try {
        const res = await fetch("/api/dashboard/sales");
        if (!res.ok) {
            const txt = await res.text();
            console.error("Gagal ambil dashboard:", txt);
            return;
        }

        const data = await res.json();
        console.log("Dashboard data:", data);


        // ====== Periode & Cards ======
        if (data.period_start && data.period_end) {
            document.getElementById("periode-text").textContent =
                `Periode: ${data.period_start} s/d ${data.period_end}`;
        }

        document.getElementById("card-total-sales").textContent =
            formatRupiah(data.total_sales || 0);

        document.getElementById("card-customer-count").textContent =
            (data.customer_count || 0).toString();

        if (data.top_customers && data.top_customers.length > 0) {
            const top = data.top_customers[0];
            document.getElementById("card-top-customer").textContent =
                `${top.name} (${formatRupiah(top.total_sales)})`;
        } else {
            document.getElementById("card-top-customer").textContent = "-";
        }

        // ====== TOP CUSTOMER BAR ======
        const custLabels = (data.top_customers || []).map(c => c.name);
        const custValues = (data.top_customers || []).map(c => c.total_sales);

        const ctxTopCust = document.getElementById("chart-top-customers").getContext("2d");
        if (chartTopCustomers) chartTopCustomers.destroy();
        chartTopCustomers = new Chart(ctxTopCust, {
            type: "bar",
            data: {
                labels: custLabels,
                datasets: [{
                    label: "Total Penjualan",
                    data: custValues
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: { ticks: { callback: v => v.toLocaleString("id-ID") } }
                }
            }
        });

        // ====== PIE KOMPOSISI CUSTOMER ======
        const ctxPieCust = document.getElementById("chart-pie-customers").getContext("2d");
        if (chartPieCustomers) chartPieCustomers.destroy();
        chartPieCustomers = new Chart(ctxPieCust, {
            type: "pie",
            data: {
                labels: custLabels,
                datasets: [{
                    data: custValues
                }]
            },
            options: { responsive: true }
        });

        // ====== TOP SALESMAN ======
        const salesLabels = (data.top_salesmen || []).map(s => s.name);
        const salesValues = (data.top_salesmen || []).map(s => s.total_sales);

        const ctxTopSales = document.getElementById("chart-top-salesmen").getContext("2d");
        if (chartTopSalesmen) chartTopSalesmen.destroy();
        chartTopSalesmen = new Chart(ctxTopSales, {
            type: "bar",
            data: {
                labels: salesLabels,
                datasets: [{
                    label: "Total Penjualan",
                    data: salesValues
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: { ticks: { callback: v => v.toLocaleString("id-ID") } }
                }
            }
        });

        // ====== TOP ITEMS ======
        const itemLabels = (data.top_items || []).map(i => i.name);
        const itemValues = (data.top_items || []).map(i => i.total_sales);

        const ctxTopItems = document.getElementById("chart-top-items").getContext("2d");
        if (chartTopItems) chartTopItems.destroy();
        chartTopItems = new Chart(ctxTopItems, {
            type: "bar",
            data: {
                labels: itemLabels,
                datasets: [{
                    label: "Total Penjualan",
                    data: itemValues
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: { ticks: { callback: v => v.toLocaleString("id-ID") } }
                }
            }
        });

        // ====== COMPARE SALESMAN (BULAN INI VS LALU) ======
        const compSalesLabels = (data.salesman_compare || []).map(s => s.name);
        const compSalesCur = (data.salesman_compare || []).map(s => s.current_month);
        const compSalesPrev = (data.salesman_compare || []).map(s => s.previous_month);

        const ctxSalesComp = document.getElementById("chart-salesman-compare").getContext("2d");
        if (chartSalesmanCompare) chartSalesmanCompare.destroy();
        chartSalesmanCompare = new Chart(ctxSalesComp, {
            type: "bar",
            data: {
                labels: compSalesLabels,
                datasets: [
                    { label: "Bulan ini", data: compSalesCur },
                    { label: "Bulan lalu", data: compSalesPrev }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    y: { ticks: { callback: v => v.toLocaleString("id-ID") } }
                }
            }
        });

        // ====== COMPARE ITEMS (BULAN INI VS LALU) ======
        const compItemLabels = (data.item_compare || []).map(s => s.name);
        const compItemCur = (data.item_compare || []).map(s => s.current_month);
        const compItemPrev = (data.item_compare || []).map(s => s.previous_month);

        const ctxItemComp = document.getElementById("chart-item-compare").getContext("2d");
        if (chartItemCompare) chartItemCompare.destroy();
        chartItemCompare = new Chart(ctxItemComp, {
            type: "bar",
            data: {
                labels: compItemLabels,
                datasets: [
                    { label: "Bulan ini", data: compItemCur },
                    { label: "Bulan lalu", data: compItemPrev }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    y: { ticks: { callback: v => v.toLocaleString("id-ID") } }
                }
            }
        });

        // ====== ANALISA OVERALL ======
        const oc = data.overall_change || {
            current_month_total: 0,
            previous_month_total: 0,
            change: 0,
            change_percent: 0
        };

        const ocText = `Bulan ini: ${formatRupiah(oc.current_month_total)}, ` +
            `Bulan lalu: ${formatRupiah(oc.previous_month_total)}, ` +
            `Perubahan: ${formatRupiah(oc.change)} ` +
            `(${oc.change_percent.toFixed(2)}%)`;

        document.getElementById("overall-change-text").textContent = ocText;

    } catch (err) {
        console.error("Error JS:", err);
    }
}

// ====== HANDLER UPLOAD ======
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("upload-form");
    const fileInput = document.getElementById("file-input");
    const statusEl = document.getElementById("upload-status");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        statusEl.textContent = "";

        if (!fileInput.files || fileInput.files.length === 0) {
            alert("Silakan pilih file HTML dulu.");
            return;
        }

        const fd = new FormData();
        fd.append("file", fileInput.files[0]);

        const res = await fetch("/api/upload/sales-html", {
            method: "POST",
            body: fd
        });

        if (!res.ok) {
            const txt = await res.text();
            alert("Gagal upload: " + txt);
            return;
        }

        const json = await res.json();
        statusEl.textContent = json.message || "Berhasil diimport.";
        fileInput.value = "";

        // Setelah upload, reload dashboard
        await loadDashboard();
    });

    // Pertama kali load halaman, langsung ambil data dashboard
    loadDashboard();
});