import dayjs from "dayjs";

/** "2024-03" -> "Mar 2024" */
export function monthLabel(month: string): string {
  return dayjs(`${month}-01`).format("MMM YYYY");
}
