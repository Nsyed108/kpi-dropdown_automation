
from setup_driver import setup_driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

USERNAME = "accounting@sypore.com"
PASSWORD = "Ammar@aja1"
TARGET_EMAIL = "zahid@sypore.com"
PORTAL_URL = "https://portal.sypore.net/auth"
OUTPUT_FILE = "kpi_report_status.txt"


def login(driver, wait):
    driver.get(PORTAL_URL)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='pat@example.com']"))).send_keys(USERNAME)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']"))).send_keys(PASSWORD)
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.sign-in-btn"))).click()
    wait.until(EC.url_contains("/billing-companies"))


def go_to_delegate_access(driver, wait):
    wait.until(EC.url_contains("/billing-companies"))
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "mat-table")))

    search_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[matinput]")))
    search_box.clear()
    search_box.send_keys(TARGET_EMAIL)

    row = wait.until(EC.presence_of_element_located(
        (By.XPATH, f"//mat-row[.//p[contains(text(), '{TARGET_EMAIL}')]]")
    ))

    more_button = wait.until(EC.element_to_be_clickable(
        (By.XPATH, f"//mat-row[.//p[contains(text(), '{TARGET_EMAIL}')]]//button[contains(., 'More')]")
    ))
    driver.execute_script("arguments[0].click();", more_button)
    time.sleep(1)

    delegate_btn = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//button[.//mat-icon[text()='send'] and .//span[contains(text(), 'Delegate')]]")
    ))
    driver.execute_script("arguments[0].click();", delegate_btn)
    wait.until(EC.url_contains("/home"))


def go_to_dashboard(driver, wait):
    driver.get("https://portal.sypore.net/dashboard")


def wait_for_kpi_response(driver, timeout=10):
    import json
    for _ in range(timeout * 2):  # check every 0.5s
        logs = driver.get_log("performance")
        for entry in logs:
            try:
                message = json.loads(entry["message"])["message"]
                if (
                    message["method"] == "Network.responseReceived"
                    and "response" in message["params"]
                    and "url" in message["params"]["response"]
                    and "kpi" in message["params"]["response"]["url"].lower()
                    and message["params"]["response"]["status"] == 200
                ):
                    return True
            except:
                continue
        time.sleep(0.5)
    return False


def run_kpi_reports(driver, wait, customer_name):
    wait.until(EC.element_to_be_clickable((By.ID, "dashboard_panel_input_customer"))).click()
    time.sleep(0.5)

    search_input = wait.until(EC.presence_of_element_located((
        By.CSS_SELECTOR,
        "ngx-mat-select-search input.mat-select-search-input[placeholder='Find Customers...']:not(.mat-select-search-hidden)"
    )))
    driver.execute_script(
        "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input'));",
        search_input,
        customer_name
    )
    time.sleep(1)
    first_customer = wait.until(EC.element_to_be_clickable((
        By.XPATH, f"//mat-option[not(contains(@class,'mat-mdc-option-disabled'))]//span[contains(text(), '{customer_name}')]"
    )))
    driver.execute_script("arguments[0].click();", first_customer)

    wait.until(EC.element_to_be_clickable((By.ID, "dashboard_panel_input_kpi"))).click()
    time.sleep(1)
    kpi_elements = wait.until(EC.presence_of_all_elements_located(
        (By.XPATH, "//mat-option[starts-with(@id, 'dashboard_panel_option_kpi_')]")
    ))

    kpi_names = []
    for el in kpi_elements:
        text = el.text.strip()
        if text and text != 'Select KPI':
            kpi_names.append(text)

    status_report = []

    for kpi in kpi_names:
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "dashboard_panel_input_kpi"))).click()
            time.sleep(0.3)
            wait.until(EC.element_to_be_clickable((By.XPATH, f"//mat-option[@id='dashboard_panel_option_kpi_{kpi}']"))).click()

            if not wait_for_kpi_response(driver, timeout=10):
                status_report.append(f"{kpi}: ❌ Failed")
                continue

            try:
                driver.find_element(By.ID, "dashboard_panel_dropdown_dynamic_range")
            except:
                status_report.append(f"{kpi}: ⚠️ No Date Range Available")
                continue

            wait.until(EC.element_to_be_clickable((By.ID, "dashboard_panel_dropdown_dynamic_range"))).click()
            time.sleep(0.2)
            wait.until(EC.element_to_be_clickable((By.XPATH, "//mat-option//span[contains(text(), 'This Week')]"))).click()

            run_btn = wait.until(EC.element_to_be_clickable((By.ID, "dashboard_panel_btn_run_report")))
            driver.execute_script("arguments[0].click();", run_btn)
            time.sleep(3)

            if "No data to display" in driver.page_source:
                status_report.append(f"{kpi}: ❌ Failed")
            elif "error" in driver.page_source.lower():
                status_report.append(f"{kpi}: ❌ Failed")
            else:
                status_report.append(f"{kpi}: ✅ Pass")

        except:
            status_report.append(f"{kpi}: ❌ Failed")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(status_report))

    print("✅ KPI run complete. Results written to kpi_report_status.txt")


if __name__ == "__main__":
    driver, wait = setup_driver()
    try:
        login(driver, wait)
        go_to_delegate_access(driver, wait)
        go_to_dashboard(driver, wait)
        run_kpi_reports(driver, wait, "Mira Genetix")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        time.sleep(2)
        driver.quit()