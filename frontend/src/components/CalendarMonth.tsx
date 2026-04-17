type Props = {
  month: Date;
  selectedDateKey: string;
  markedDates?: Set<string>;
  onSelectDateKey: (dateKey: string) => void;
};

function pad2(value: number) {
  return String(value).padStart(2, "0");
}

function dateKeyLocal(date: Date) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

function startOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function endOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0);
}

function addDays(date: Date, days: number) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

// Monday=0 ... Sunday=6
function weekDayMondayFirst(date: Date) {
  const day = date.getDay(); // Sunday=0 ... Saturday=6
  return (day + 6) % 7;
}

export function CalendarMonth({
  month,
  selectedDateKey,
  markedDates,
  onSelectDateKey,
}: Props) {
  const monthStart = startOfMonth(month);
  const monthEnd = endOfMonth(month);

  const gridStart = addDays(monthStart, -weekDayMondayFirst(monthStart));
  const gridEnd = addDays(monthEnd, 6 - weekDayMondayFirst(monthEnd));

  const cells: Date[] = [];
  for (let d = gridStart; d <= gridEnd; d = addDays(d, 1)) {
    cells.push(d);
  }

  return (
    <div className="calendar">
      <div className="calendarHeader">
        <div className="calendarTitle">
          {month.toLocaleDateString(undefined, { month: "long", year: "numeric" })}
        </div>
        <div className="calendarLegend muted">
          Click a day to pick shifts
        </div>
      </div>

      <div className="calendarWeekdays muted">
        <div>Mon</div>
        <div>Tue</div>
        <div>Wed</div>
        <div>Thu</div>
        <div>Fri</div>
        <div>Sat</div>
        <div>Sun</div>
      </div>

      <div className="calendarGrid">
        {cells.map((date) => {
          const key = dateKeyLocal(date);
          const isOutside = date.getMonth() !== month.getMonth();
          const isSelected = key === selectedDateKey;
          const isMarked = markedDates?.has(key) ?? false;

          return (
            <button
              key={key}
              type="button"
              className="calendarCell"
              onClick={() => onSelectDateKey(key)}
              style={{
                opacity: isOutside ? 0.45 : 1,
                borderColor: isSelected ? "rgba(99,102,241,0.8)" : undefined,
                background: isSelected ? "rgba(99,102,241,0.16)" : undefined,
              }}
            >
              <div className="calendarCellTop">
                <div className="calendarDay">{date.getDate()}</div>
                {isMarked ? <div className="calendarDot" /> : null}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
