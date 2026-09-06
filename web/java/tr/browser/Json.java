package tr.browser;

import java.lang.reflect.Array;
import java.util.Map;

/** Small dependency-free output serializer. Input remains Java Properties. */
public final class Json {
    private Json() {}
    public static String encode(final Object value) {
        final StringBuilder out = new StringBuilder();
        append(out, value);
        return out.toString();
    }
    private static void append(final StringBuilder out, final Object value) {
        if (value == null) { out.append("null"); return; }
        if (value instanceof String text) {
            out.append('"');
            for (int i = 0; i < text.length(); i++) {
                final char ch = text.charAt(i);
                if (ch == '"' || ch == '\\') out.append('\\').append(ch);
                else if (ch < 32 || ch == '\u2028' || ch == '\u2029')
                    out.append(String.format("\\u%04x", (int) ch));
                else out.append(ch);
            }
            out.append('"');
        } else if (value instanceof Number || value instanceof Boolean) out.append(value);
        else if (value instanceof Map<?, ?> map) {
            out.append('{'); boolean comma = false;
            for (final var entry : map.entrySet()) {
                if (comma) out.append(','); comma = true;
                append(out, entry.getKey().toString()); out.append(':'); append(out, entry.getValue());
            }
            out.append('}');
        } else if (value instanceof Iterable<?> list) {
            out.append('['); boolean comma = false;
            for (final Object entry : list) { if (comma) out.append(','); comma = true; append(out, entry); }
            out.append(']');
        } else if (value.getClass().isArray()) {
            out.append('[');
            for (int i = 0; i < Array.getLength(value); i++) {
                if (i != 0) out.append(','); append(out, Array.get(value, i));
            }
            out.append(']');
        } else throw new IllegalArgumentException("Unsupported JSON value " + value.getClass());
    }
}
