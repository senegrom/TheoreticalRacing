package tr.browser;

import java.util.AbstractList;
import java.util.List;

/** Read-only reverse view, used only by TrackGeometry's read-only iteration. */
public final class Lists {
    private Lists() {}
    public static <T> List<T> reversed(final List<T> source) {
        return new AbstractList<>() {
            @Override public T get(final int index) {
                if (index < 0 || index >= size()) throw new IndexOutOfBoundsException(index);
                return source.get(source.size() - 1 - index);
            }
            @Override public int size() { return source.size(); }
        };
    }
}
