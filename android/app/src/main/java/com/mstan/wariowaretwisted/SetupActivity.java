package com.mstan.wariowaretwisted;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.hardware.Sensor;
import android.hardware.SensorManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.view.Gravity;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class SetupActivity extends Activity {
    private static final int PICK_BIOS = 1001;
    private static final int PICK_ROM = 1002;
    private static final long BIOS_SIZE = 16 * 1024;
    private static final long ROM_SIZE = 16 * 1024 * 1024;
    private static final String BIOS_SHA1 =
        "300c20df6731a33952ded8c436f7f186d25d3492";
    private static final String ROM_SHA1 =
        "f0102d0d6f7596fe853d5d0a94682718278e083a";

    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private TextView biosStatus;
    private TextView romStatus;
    private TextView motionStatus;
    private Button playButton;
    private Button biosButton;
    private Button romButton;
    private boolean biosReady;
    private boolean romReady;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
        if (hasBundledPrivateAssets()) {
            startActivity(new Intent(this, WarioWareActivity.class));
            finish();
            return;
        }
        setContentView(buildContent());
        enterImmersiveMode();
        refreshStatus();
    }

    @Override
    protected void onResume() {
        super.onResume();
        enterImmersiveMode();
        if (playButton != null) {
            refreshStatus();
        }
    }

    @Override
    protected void onDestroy() {
        worker.shutdownNow();
        super.onDestroy();
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            enterImmersiveMode();
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (resultCode != RESULT_OK || data == null || data.getData() == null) {
            return;
        }
        if (requestCode != PICK_BIOS && requestCode != PICK_ROM) {
            return;
        }

        final boolean bios = requestCode == PICK_BIOS;
        final Uri uri = data.getData();
        setBusy(true, bios ? "Checking BIOS…" : "Checking ROM…");
        worker.execute(() -> {
            try {
                installVerifiedAsset(uri, bios);
                runOnUiThread(() -> {
                    setBusy(false, null);
                    refreshStatus();
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    setBusy(false, null);
                    refreshStatus();
                    showError(bios ? "BIOS not accepted" : "ROM not accepted",
                        error.getMessage());
                });
            }
        });
    }

    private View buildContent() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(Color.rgb(9, 11, 24));

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER_HORIZONTAL);
        root.setPadding(dp(36), dp(22), dp(36), dp(28));
        scroll.addView(root, new ScrollView.LayoutParams(
            ScrollView.LayoutParams.MATCH_PARENT,
            ScrollView.LayoutParams.WRAP_CONTENT));

        TextView eyebrow = text("ANDROID EDITION", 12, Color.rgb(78, 216, 255));
        eyebrow.setTypeface(Typeface.DEFAULT_BOLD);
        eyebrow.setLetterSpacing(0.16f);
        root.addView(eyebrow);

        TextView title = text(getString(R.string.setup_title), 30, Color.WHITE);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setGravity(Gravity.CENTER);
        root.addView(title, margins(dp(720), -1, 0, dp(2), 0, 0));

        TextView subtitle = text(getString(R.string.setup_subtitle), 15,
            Color.rgb(177, 187, 216));
        subtitle.setGravity(Gravity.CENTER);
        root.addView(subtitle, margins(dp(720), -1, 0, 0, 0, dp(18)));

        LinearLayout assets = new LinearLayout(this);
        assets.setOrientation(LinearLayout.HORIZONTAL);
        assets.setGravity(Gravity.CENTER);
        root.addView(assets, margins(-1, -2, 0, 0, 0, dp(14)));

        LinearLayout biosCard = assetCard("1", "GBA BIOS",
            "Choose your clean 16 KiB gba_bios.bin dump.");
        biosStatus = statusText();
        biosButton = actionButton("CHOOSE BIOS");
        biosButton.setOnClickListener(view -> pickFile(PICK_BIOS));
        biosCard.addView(biosStatus, margins(-1, -2, 0, dp(8), 0, dp(8)));
        biosCard.addView(biosButton, margins(-1, dp(48), 0, 0, 0, 0));
        assets.addView(biosCard, weightedMargins(1, dp(8), 0, dp(8), 0));

        LinearLayout romCard = assetCard("2", "WarioWare: Twisted! ROM",
            "Choose your clean USA .gba cartridge dump.");
        romStatus = statusText();
        romButton = actionButton("CHOOSE ROM");
        romButton.setOnClickListener(view -> pickFile(PICK_ROM));
        romCard.addView(romStatus, margins(-1, -2, 0, dp(8), 0, dp(8)));
        romCard.addView(romButton, margins(-1, dp(48), 0, 0, 0, 0));
        assets.addView(romCard, weightedMargins(1, dp(8), 0, dp(8), 0));

        motionStatus = text("", 13, Color.rgb(177, 187, 216));
        motionStatus.setGravity(Gravity.CENTER);
        root.addView(motionStatus, margins(dp(720), -1, 0, 0, 0, dp(12)));

        playButton = actionButton("PLAY");
        playButton.setTextSize(18);
        playButton.setTypeface(Typeface.DEFAULT_BOLD);
        playButton.setOnClickListener(view -> launchGame());
        root.addView(playButton, margins(dp(360), dp(58), 0, 0, 0, dp(14)));

        TextView privacy = text(
            "Your BIOS and ROM stay in this app’s private storage. " +
            "They are not included in the APK. Rotate the phone around its " +
            "screen-normal axis to play; touch and gamepads are also supported.",
            12, Color.rgb(132, 143, 173));
        privacy.setGravity(Gravity.CENTER);
        root.addView(privacy, margins(dp(760), -1, 0, 0, 0, 0));
        return scroll;
    }

    private LinearLayout assetCard(String number, String title, String body) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(20), dp(15), dp(20), dp(17));
        card.setBackground(roundRect(Color.rgb(20, 25, 48), 18,
            Color.rgb(48, 58, 92)));

        TextView step = text(number + "  " + title, 17, Color.WHITE);
        step.setTypeface(Typeface.DEFAULT_BOLD);
        card.addView(step);
        TextView description = text(body, 13, Color.rgb(164, 175, 207));
        card.addView(description, margins(-1, -2, 0, dp(4), 0, 0));
        return card;
    }

    private TextView statusText() {
        TextView status = text("Checking…", 13, Color.rgb(255, 211, 78));
        status.setTypeface(Typeface.DEFAULT_BOLD);
        return status;
    }

    private Button actionButton(String label) {
        Button button = new Button(this);
        button.setText(label);
        button.setTextColor(Color.rgb(8, 16, 27));
        button.setTextSize(13);
        button.setTypeface(Typeface.DEFAULT_BOLD);
        button.setAllCaps(false);
        button.setGravity(Gravity.CENTER);
        button.setPadding(dp(16), 0, dp(16), 0);
        button.setBackground(roundRect(Color.rgb(78, 216, 255), 14,
            Color.TRANSPARENT));
        return button;
    }

    private TextView text(String value, float size, int color) {
        TextView text = new TextView(this);
        text.setText(value);
        text.setTextSize(size);
        text.setTextColor(color);
        text.setLineSpacing(0, 1.12f);
        return text;
    }

    private void refreshStatus() {
        biosReady = matchesInstalled(new File(getFilesDir(), "bios/gba_bios.bin"),
            BIOS_SIZE);
        romReady = matchesInstalled(
            new File(getFilesDir(), "roms/warioware_twisted_usa.gba"), ROM_SIZE);

        setAssetStatus(biosStatus, biosButton, biosReady, "BIOS");
        setAssetStatus(romStatus, romButton, romReady, "ROM");
        playButton.setEnabled(biosReady && romReady);
        playButton.setAlpha(playButton.isEnabled() ? 1.0f : 0.35f);

        SensorManager manager = (SensorManager) getSystemService(SENSOR_SERVICE);
        Sensor gyro = manager == null ? null :
            manager.getDefaultSensor(Sensor.TYPE_GYROSCOPE);
        if (gyro != null) {
            motionStatus.setText("●  Device gyroscope ready  ·  " + gyro.getName());
            motionStatus.setTextColor(Color.rgb(120, 235, 171));
        } else {
            motionStatus.setText(
                "Device gyroscope unavailable — controller motion still works.");
            motionStatus.setTextColor(Color.rgb(255, 184, 104));
        }
    }

    private void setAssetStatus(TextView status, Button button,
                                boolean ready, String kind) {
        status.setText(ready ? "●  Verified and ready" : "○  " + kind + " required");
        status.setTextColor(ready ? Color.rgb(120, 235, 171) :
            Color.rgb(255, 211, 78));
        button.setText(ready ? "REPLACE " + kind : "CHOOSE " + kind);
    }

    private void pickFile(int requestCode) {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        // Android's DocumentsUI frequently assigns .bin and .gba files an
        // unknown or vendor-specific MIME type. Filtering for octet-stream
        // therefore makes valid dumps disappear on some providers. Show every
        // openable file here and let the strict size + SHA-1 check below decide
        // whether the selected document is the required BIOS or ROM.
        intent.setType("*/*");
        startActivityForResult(intent, requestCode);
    }

    private void launchGame() {
        if (!biosReady || !romReady) {
            return;
        }
        startActivity(new Intent(this, WarioWareActivity.class));
    }

    private boolean hasBundledPrivateAssets() {
        try (InputStream bios = getAssets().open("payload/bios/gba_bios.bin");
             InputStream rom = getAssets().open(
                 "payload/roms/warioware_twisted_usa.gba")) {
            return bios.read() >= 0 && rom.read() >= 0;
        } catch (IOException ignored) {
            return false;
        }
    }

    private void installVerifiedAsset(Uri uri, boolean bios)
            throws IOException, NoSuchAlgorithmException {
        String displayName = displayName(uri);
        long expectedSize = bios ? BIOS_SIZE : ROM_SIZE;
        String expectedSha1 = bios ? BIOS_SHA1 : ROM_SHA1;
        File directory = new File(getFilesDir(), bios ? "bios" : "roms");
        if (!directory.isDirectory() && !directory.mkdirs()) {
            throw new IOException("Could not create the private game directory.");
        }
        File destination = new File(directory,
            bios ? "gba_bios.bin" : "warioware_twisted_usa.gba");
        File temporary = File.createTempFile("import-", ".tmp", directory);
        MessageDigest digest = MessageDigest.getInstance("SHA-1");
        long total = 0;

        try (InputStream input = getContentResolver().openInputStream(uri);
             FileOutputStream output = new FileOutputStream(temporary)) {
            if (input == null) {
                throw new IOException("Android could not open " + displayName + ".");
            }
            byte[] buffer = new byte[1024 * 1024];
            int read;
            while ((read = input.read(buffer)) >= 0) {
                if (read == 0) {
                    continue;
                }
                total += read;
                if (total > expectedSize) {
                    throw new IOException(displayName + " is larger than expected.");
                }
                digest.update(buffer, 0, read);
                output.write(buffer, 0, read);
            }
            output.getFD().sync();
        } catch (IOException error) {
            temporary.delete();
            throw error;
        }

        String actualSha1 = toHex(digest.digest());
        if (total != expectedSize || !expectedSha1.equals(actualSha1)) {
            temporary.delete();
            throw new IOException(String.format(Locale.US,
                "%s is not the supported clean %s dump.\n\n" +
                "Size: %,d bytes (expected %,d)\nSHA-1: %s",
                displayName, bios ? "GBA BIOS" : "USA WarioWare ROM",
                total, expectedSize, actualSha1));
        }

        if (destination.exists() && !destination.delete()) {
            temporary.delete();
            throw new IOException("Could not replace the previously imported file.");
        }
        if (!temporary.renameTo(destination)) {
            copyFile(temporary, destination);
            temporary.delete();
        }
    }

    private boolean matchesInstalled(File file, long expectedSize) {
        return file.isFile() && file.length() == expectedSize;
    }

    private static void copyFile(File source, File destination) throws IOException {
        try (FileInputStream input = new FileInputStream(source);
             FileOutputStream output = new FileOutputStream(destination)) {
            byte[] buffer = new byte[1024 * 1024];
            int read;
            while ((read = input.read(buffer)) >= 0) {
                if (read > 0) {
                    output.write(buffer, 0, read);
                }
            }
            output.getFD().sync();
        }
    }

    private String displayName(Uri uri) {
        try (android.database.Cursor cursor = getContentResolver().query(
                uri, new String[] {OpenableColumns.DISPLAY_NAME},
                null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int column = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (column >= 0) {
                    return cursor.getString(column);
                }
            }
        } catch (Exception ignored) {
        }
        return "selected file";
    }

    private void setBusy(boolean busy, String label) {
        biosButton.setEnabled(!busy);
        romButton.setEnabled(!busy);
        playButton.setEnabled(!busy && biosReady && romReady);
        if (busy && label != null) {
            motionStatus.setText(label);
            motionStatus.setTextColor(Color.rgb(78, 216, 255));
        }
    }

    private void showError(String title, String message) {
        new AlertDialog.Builder(this)
            .setTitle(title)
            .setMessage(message == null ? "The selected file could not be read." : message)
            .setPositiveButton("OK", null)
            .show();
    }

    private void enterImmersiveMode() {
        if (Build.VERSION.SDK_INT >= 30) {
            WindowInsetsController controller = getWindow().getInsetsController();
            if (controller != null) {
                controller.hide(WindowInsets.Type.statusBars()
                    | WindowInsets.Type.navigationBars());
                controller.setSystemBarsBehavior(
                    WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
            }
        } else {
            getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                    | View.SYSTEM_UI_FLAG_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                    | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                    | View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
        }
    }

    private GradientDrawable roundRect(int color, int radiusDp, int strokeColor) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(color);
        drawable.setCornerRadius(dp(radiusDp));
        if (strokeColor != Color.TRANSPARENT) {
            drawable.setStroke(dp(1), strokeColor);
        }
        return drawable;
    }

    private LinearLayout.LayoutParams margins(int width, int height,
                                               int left, int top,
                                               int right, int bottom) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
            width, height);
        params.setMargins(left, top, right, bottom);
        return params;
    }

    private LinearLayout.LayoutParams weightedMargins(float weight,
                                                       int left, int top,
                                                       int right, int bottom) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
            0, LinearLayout.LayoutParams.WRAP_CONTENT, weight);
        params.setMargins(left, top, right, bottom);
        return params;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private static String toHex(byte[] bytes) {
        StringBuilder value = new StringBuilder(bytes.length * 2);
        for (byte item : bytes) {
            value.append(String.format(Locale.US, "%02x", item & 0xff));
        }
        return value.toString();
    }
}
