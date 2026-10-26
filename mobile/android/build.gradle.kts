allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}

// geolocator_android dan flutter_secure_storage masih mengompilasi Java 8,
// sehingga setiap build mencetak "source value 8 is obsolete".
subprojects {
    if (name != "geolocator_android" && name != "flutter_secure_storage") return@subprojects
    afterEvaluate {
        runCatching {
            val android = extensions.findByName("android") ?: return@runCatching
            val compileOptions = android.javaClass.getMethod("getCompileOptions").invoke(android)
            compileOptions.javaClass
                .getMethod("setSourceCompatibility", JavaVersion::class.java)
                .invoke(compileOptions, JavaVersion.VERSION_17)
            compileOptions.javaClass
                .getMethod("setTargetCompatibility", JavaVersion::class.java)
                .invoke(compileOptions, JavaVersion.VERSION_17)
        }
    }
}

// google_mlkit_commons 0.13 mencetak peringatan tipe Kotlin pada path file
// yang tidak dipakai alur kamera. Matikan peringatan modul itu saja.
subprojects {
    if (name != "google_mlkit_commons") return@subprojects
    afterEvaluate {
        runCatching {
            val kotlinExt = extensions.findByName("kotlin") ?: return@runCatching
            val compilerOptions = kotlinExt.javaClass.getMethod("getCompilerOptions").invoke(kotlinExt)
            val suppress = compilerOptions.javaClass.getMethod("getSuppressWarnings").invoke(compilerOptions)
            suppress.javaClass.methods
                .first { it.name == "set" && it.parameterCount == 1 }
                .invoke(suppress, true)
        }
    }
}

subprojects {
    project.evaluationDependsOn(":app")
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
