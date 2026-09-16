# WebView entry points are referenced by the Android framework.
-keepclassmembers class * extends android.app.Activity { public <init>(); }
