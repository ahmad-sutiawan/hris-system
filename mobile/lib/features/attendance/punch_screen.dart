import 'dart:async';
import 'dart:typed_data';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:latlong2/latlong.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/utils/shift_utils.dart';
import '../../core/widgets/animated_interactions.dart';
import '../../core/widgets/hris_widgets.dart';
import '../home/home_screen.dart';
import 'attendance_screen.dart';

enum _PunchStep { location, selfie }

class PunchScreen extends ConsumerStatefulWidget {
  const PunchScreen({super.key});

  @override
  ConsumerState<PunchScreen> createState() => _PunchScreenState();
}

class _PunchScreenState extends ConsumerState<PunchScreen> {
  final _notesController = TextEditingController();
  final _brightness = ValueNotifier<double>(0.5);
  final _mapController = MapController();

  _PunchStep _step = _PunchStep.location;
  bool _loading = false;
  bool _locating = false;
  bool _cameraReady = false;
  bool _useFrontCamera = true;
  Uint8List? _photoBytes;
  Position? _position;
  String? _locationError;
  StreamSubscription<Position>? _positionSub;
  CameraController? _cameraController;

  bool get _isClockOut {
    final action = GoRouterState.of(context).uri.queryParameters['action'];
    return action == 'out';
  }

  String get _title => _isClockOut ? 'Absen Pulang' : 'Absen Masuk';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _startLocationTracking());
  }

  @override
  void dispose() {
    _positionSub?.cancel();
    _disposeCamera();
    _notesController.dispose();
    _brightness.dispose();
    _mapController.dispose();
    super.dispose();
  }

  Future<void> _startLocationTracking() async {
    setState(() {
      _locating = true;
      _locationError = null;
    });
    try {
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        setState(() {
          _locationError = 'Izin lokasi diperlukan untuk verifikasi absensi.';
        });
        return;
      }

      await _positionSub?.cancel();
      _positionSub = Geolocator.getPositionStream(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          distanceFilter: 3,
        ),
      ).listen((pos) {
        if (!mounted) return;
        setState(() => _position = pos);
      });

      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 15),
        ),
      );
      if (mounted) setState(() => _position = pos);
    } catch (e) {
      if (mounted) {
        setState(() => _locationError = 'Gagal mendeteksi lokasi. Coba refresh.');
      }
    } finally {
      if (mounted) setState(() => _locating = false);
    }
  }

  Future<void> _refreshLocation() => _startLocationTracking();

  Future<void> _initCamera() async {
    await _disposeCamera();
    setState(() => _cameraReady = false);
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) return;

      CameraDescription selected;
      if (_useFrontCamera) {
        selected = cameras.firstWhere(
          (c) => c.lensDirection == CameraLensDirection.front,
          orElse: () => cameras.first,
        );
      } else {
        selected = cameras.firstWhere(
          (c) => c.lensDirection == CameraLensDirection.back,
          orElse: () => cameras.first,
        );
      }

      final controller = CameraController(
        selected,
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.jpeg,
      );
      await controller.initialize();
      if (!mounted) {
        await controller.dispose();
        return;
      }
      _cameraController = controller;
      setState(() => _cameraReady = true);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Kamera tidak tersedia. Izinkan akses kamera di browser.')),
        );
      }
    }
  }

  Future<void> _disposeCamera() async {
    final controller = _cameraController;
    _cameraController = null;
    _cameraReady = false;
    if (controller != null) {
      await controller.dispose();
    }
  }

  Future<void> _toggleCamera() async {
    if (_photoBytes != null) {
      setState(() => _photoBytes = null);
    }
    setState(() => _useFrontCamera = !_useFrontCamera);
    await _initCamera();
  }

  Future<void> _captureFromPreview() async {
    final controller = _cameraController;
    if (controller == null || !controller.value.isInitialized) return;
    try {
      final file = await controller.takePicture();
      final bytes = await file.readAsBytes();
      if (mounted) setState(() => _photoBytes = bytes);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Gagal ambil foto: $e')));
      }
    }
  }

  Future<void> _goToSelfieStep() async {
    await _positionSub?.cancel();
    _positionSub = null;
    setState(() => _step = _PunchStep.selfie);
    await _initCamera();
  }

  Future<void> _backFromSelfie() async {
    await _disposeCamera();
    if (mounted) {
      setState(() {
        _step = _PunchStep.location;
        _photoBytes = null;
      });
    }
  }

  Future<void> _submit() async {
    if (_step == _PunchStep.selfie && _photoBytes == null) {
      await _captureFromPreview();
    }
    if (_photoBytes == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Posisikan wajah di bingkai lalu tekan Submit.')),
        );
      }
      return;
    }

    final capturedAt = DateTime.now();
    final confirmed = await _showPunchPreviewDialog(
      photoBytes: _photoBytes!,
      capturedAt: capturedAt,
    );
    if (!confirmed || !mounted) return;

    setState(() => _loading = true);
    try {
      final encoded = ApiClient.imageToBase64DataUrl(_photoBytes!);
      final api = ref.read(apiClientProvider);
      final lat = _position?.latitude;
      final lng = _position?.longitude;
      final notes = _notesController.text.trim();
      final Map<String, dynamic> result;
      if (_isClockOut) {
        result = await api.clockOut(
          encoded,
          latitude: lat,
          longitude: lng,
          notes: notes.isEmpty ? null : notes,
        );
      } else {
        result = await api.clockIn(
          encoded,
          latitude: lat,
          longitude: lng,
          notes: notes.isEmpty ? null : notes,
        );
      }
      ref.invalidate(dashboardProvider);
      ref.invalidate(timesheetsProvider);
      if (mounted) {
        final whenRaw = _isClockOut ? result['check_out'] : result['check_in'];
        final whenLabel = _formatPunchTime(whenRaw) ?? _formatPunchTime(capturedAt.toIso8601String());
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              whenLabel == null
                  ? (_isClockOut ? 'Absen pulang berhasil.' : 'Absen masuk berhasil.')
                  : '${_isClockOut ? 'Absen pulang' : 'Absen masuk'} berhasil — $whenLabel',
            ),
            backgroundColor: AppColors.success,
          ),
        );
        context.go('/attendance');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<bool> _showPunchPreviewDialog({
    required Uint8List photoBytes,
    required DateTime capturedAt,
  }) async {
    final confirmed = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => _PunchPreviewDialog(
        photoBytes: photoBytes,
        capturedAt: capturedAt,
        isClockOut: _isClockOut,
        onRetake: () {
          setState(() => _photoBytes = null);
        },
      ),
    );
    return confirmed == true;
  }

  String? _formatPunchTime(Object? raw) {
    if (raw == null) return null;
    try {
      final parsed = DateTime.parse(raw.toString()).toLocal();
      return DateFormat('dd MMM yyyy HH:mm').format(parsed);
    } catch (_) {
      return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    final dashboard = ref.watch(dashboardProvider);
    final employee = ref.watch(authProvider).employee;

    return dashboard.when(
      loading: () => const HrisScaffold(
        body: HrisSafeBody(
          child: Center(child: CircularProgressIndicator(color: AppColors.chinaRed)),
        ),
      ),
      error: (e, _) => HrisScaffold(
        appBar: hrisAppBar(title: _title),
        body: Center(child: Text('$e')),
      ),
      data: (data) {
        final shift = data['today_shift'] as Map<String, dynamic>?;
        final location = shiftLocationLabel(shift, employee: employee);
        final timeRange = formatShiftTimeRange(shift);
        final workDate = shift?['work_date'] as String? ?? data['today'] as String?;
        final dateLabel = _formatShiftDate(workDate, timeRange);

        return HrisScaffold(
          body: HrisSafeBody(
            bottom: false,
            child: Column(
              children: [
                _TalentaPunchHeader(
                  title: _title,
                  step: _step,
                  onBack: () {
                    if (_step == _PunchStep.selfie) {
                      _backFromSelfie();
                    } else {
                      context.pop();
                    }
                  },
                  onAction: _step == _PunchStep.location ? _refreshLocation : _toggleCamera,
                  actionIcon: _step == _PunchStep.location
                      ? Icons.my_location_rounded
                      : Icons.cameraswitch_rounded,
                ),
                Transform.translate(
                  offset: const Offset(0, -18),
                  child: _TalentaShiftInfoCard(
                    location: location,
                    dateLabel: dateLabel,
                  ),
                ),
                Expanded(
                  child: _step == _PunchStep.location
                      ? _LocationStepBody(
                          mapController: _mapController,
                          locating: _locating,
                          position: _position,
                          locationError: _locationError,
                          officeLabel: location,
                        )
                      : _SelfieStepBody(
                          photoBytes: _photoBytes,
                          cameraController: _cameraController,
                          cameraReady: _cameraReady,
                          brightness: _brightness,
                        ),
                ),
                _TalentaBottomPanel(
                  step: _step,
                  loading: _loading,
                  notesController: _notesController,
                  canProceed: _step == _PunchStep.location
                      ? _position != null && !_locating
                      : _cameraReady || _photoBytes != null,
                  primaryLabel: _step == _PunchStep.location
                      ? 'Lanjut'
                      : (_isClockOut ? 'Submit Pulang' : 'Submit Masuk'),
                  onPrimary: _step == _PunchStep.location ? _goToSelfieStep : _submit,
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  String _formatShiftDate(String? isoDate, String timeRange) {
    if (isoDate == null) return timeRange;
    try {
      final date = DateTime.parse(isoDate);
      final fmt = DateFormat('dd MMM yyyy');
      if (timeRange == '—') return fmt.format(date);
      return '${fmt.format(date)} ($timeRange)';
    } catch (_) {
      return isoDate;
    }
  }
}

class _TalentaPunchHeader extends StatelessWidget {
  const _TalentaPunchHeader({
    required this.title,
    required this.step,
    required this.onBack,
    required this.onAction,
    required this.actionIcon,
  });

  final String title;
  final _PunchStep step;
  final VoidCallback onBack;
  final VoidCallback onAction;
  final IconData actionIcon;

  @override
  Widget build(BuildContext context) {
    final stepLabel = step == _PunchStep.location ? 'Langkah 1 dari 2' : 'Langkah 2 dari 2';

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(8, 8, 8, 28),
      decoration: const BoxDecoration(gradient: AppColors.headerGradient),
      child: Row(
        children: [
          IconButton(
            onPressed: onBack,
            icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 20),
          ),
          Expanded(
            child: Column(
              children: [
                Text(
                  title,
                  style: GoogleFonts.plusJakartaSans(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                    fontSize: 18,
                  ),
                ),
                Text(
                  stepLabel,
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12),
                ),
              ],
            ),
          ),
          Container(
            margin: const EdgeInsets.only(right: 4),
            decoration: BoxDecoration(
              color: step == _PunchStep.selfie
                  ? AppColors.success
                  : Colors.white.withValues(alpha: 0.18),
              borderRadius: BorderRadius.circular(10),
            ),
            child: IconButton(
              onPressed: onAction,
              icon: Icon(actionIcon, color: Colors.white, size: 20),
            ),
          ),
        ],
      ),
    );
  }
}

class _TalentaShiftInfoCard extends StatelessWidget {
  const _TalentaShiftInfoCard({required this.location, required this.dateLabel});

  final String location;
  final String dateLabel;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        boxShadow: const [
          BoxShadow(color: AppColors.cardShadow, blurRadius: 24, offset: Offset(0, 10)),
        ],
        border: Border.all(color: AppColors.darkGoldMuted),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            location,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: AppColors.textMuted,
            ),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              const Icon(Icons.calendar_today_rounded, size: 16, color: AppColors.darkGold),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  dateLabel,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 15,
                    fontWeight: FontWeight.w800,
                    color: AppColors.text,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _LocationStepBody extends StatelessWidget {
  const _LocationStepBody({
    required this.mapController,
    required this.locating,
    required this.position,
    required this.locationError,
    required this.officeLabel,
  });

  final MapController mapController;
  final bool locating;
  final Position? position;
  final String? locationError;
  final String officeLabel;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        _LiveMapView(
          mapController: mapController,
          position: position,
        ),
        if (locating)
          Container(
            color: Colors.black.withValues(alpha: 0.12),
            child: const Center(child: CircularProgressIndicator(color: AppColors.chinaRed)),
          ),
        Positioned(
          left: 16,
          right: 16,
          bottom: 16,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (locationError != null)
                _InfoChip(
                  icon: Icons.error_outline_rounded,
                  label: locationError!,
                  color: AppColors.danger,
                  bg: AppColors.dangerDim,
                )
              else if (position != null) ...[
                _InfoChip(
                  icon: Icons.gps_fixed_rounded,
                  label: 'Live GPS · $officeLabel',
                  color: AppColors.success,
                  bg: AppColors.successDim,
                ),
                const SizedBox(height: 8),
                _InfoChip(
                  icon: Icons.location_on_rounded,
                  label:
                      '${position!.latitude.toStringAsFixed(5)}, ${position!.longitude.toStringAsFixed(5)}',
                  color: AppColors.darkGoldRich,
                  bg: AppColors.darkGoldLight,
                ),
              ] else if (!locating)
                _InfoChip(
                  icon: Icons.location_searching_rounded,
                  label: 'Menunggu sinyal GPS...',
                  color: AppColors.darkGold,
                  bg: AppColors.darkGoldLight,
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _LiveMapView extends StatefulWidget {
  const _LiveMapView({required this.mapController, required this.position});

  final MapController mapController;
  final Position? position;

  @override
  State<_LiveMapView> createState() => _LiveMapViewState();
}

class _LiveMapViewState extends State<_LiveMapView> {
  LatLng? _lastCenter;

  @override
  void didUpdateWidget(covariant _LiveMapView oldWidget) {
    super.didUpdateWidget(oldWidget);
    _syncMapCenter();
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _syncMapCenter());
  }

  void _syncMapCenter() {
    final pos = widget.position;
    if (pos == null) return;
    final target = LatLng(pos.latitude, pos.longitude);
    if (_lastCenter != null &&
        _lastCenter!.latitude == target.latitude &&
        _lastCenter!.longitude == target.longitude) {
      return;
    }
    _lastCenter = target;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      try {
        final zoom = widget.mapController.camera.zoom;
        widget.mapController.move(target, zoom > 0 ? zoom : 17);
      } catch (_) {
        widget.mapController.move(target, 17);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    if (widget.position == null) {
      return Container(
        color: const Color(0xFFE8EDE4),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const CircularProgressIndicator(color: AppColors.chinaRed),
              const SizedBox(height: 12),
              Text(
                'Memuat peta...',
                style: GoogleFonts.plusJakartaSans(color: AppColors.textMuted),
              ),
            ],
          ),
        ),
      );
    }

    final point = LatLng(widget.position!.latitude, widget.position!.longitude);

    return FlutterMap(
      mapController: widget.mapController,
      options: MapOptions(
        initialCenter: point,
        initialZoom: 17,
        minZoom: 5,
        maxZoom: 19,
      ),
      children: [
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'com.bps.hris_mobile',
        ),
        MarkerLayer(
          markers: [
            Marker(
              point: point,
              width: 64,
              height: 72,
              alignment: Alignment.topCenter,
              child: Column(
                children: [
                  Container(
                    width: 52,
                    height: 52,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: AppColors.surface,
                      border: Border.all(color: AppColors.info, width: 3),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.25),
                          blurRadius: 8,
                          offset: const Offset(0, 3),
                        ),
                      ],
                    ),
                    child: const Icon(Icons.person_rounded, color: AppColors.chinaRed, size: 30),
                  ),
                  Container(
                    width: 12,
                    height: 12,
                    decoration: BoxDecoration(
                      color: AppColors.info.withValues(alpha: 0.45),
                      shape: BoxShape.circle,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _SelfieStepBody extends StatelessWidget {
  const _SelfieStepBody({
    required this.photoBytes,
    required this.cameraController,
    required this.cameraReady,
    required this.brightness,
  });

  final Uint8List? photoBytes;
  final CameraController? cameraController;
  final bool cameraReady;
  final ValueNotifier<double> brightness;

  @override
  Widget build(BuildContext context) {
    final hasPhoto = photoBytes != null;
    final showPreview = cameraReady && cameraController != null && !hasPhoto;

    return Stack(
      fit: StackFit.expand,
      children: [
        ColoredBox(
          color: const Color(0xFF2A2A2A),
          child: hasPhoto
              ? Image.memory(photoBytes!, fit: BoxFit.cover, width: double.infinity)
              : showPreview
                  ? FittedBox(
                      fit: BoxFit.cover,
                      clipBehavior: Clip.hardEdge,
                      child: SizedBox(
                        width: cameraController!.value.previewSize?.height ?? 1,
                        height: cameraController!.value.previewSize?.width ?? 1,
                        child: CameraPreview(cameraController!),
                      ),
                    )
                  : Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const CircularProgressIndicator(color: Colors.white),
                          const SizedBox(height: 12),
                          Text(
                            'Menyiapkan kamera...',
                            style: GoogleFonts.plusJakartaSans(color: Colors.white70),
                          ),
                        ],
                      ),
                    ),
        ),
        Positioned(
          left: 32,
          right: 32,
          bottom: 20,
          child: ValueListenableBuilder<double>(
            valueListenable: brightness,
            builder: (_, value, __) {
              return Row(
                children: [
                  Icon(Icons.wb_sunny_outlined, color: Colors.white.withValues(alpha: 0.85), size: 18),
                  Expanded(
                    child: SliderTheme(
                      data: SliderThemeData(
                        trackHeight: 2,
                        thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6),
                        overlayShape: SliderComponentShape.noOverlay,
                        activeTrackColor: Colors.white,
                        inactiveTrackColor: Colors.white.withValues(alpha: 0.35),
                        thumbColor: Colors.white,
                      ),
                      child: Slider(
                        value: value,
                        onChanged: (v) => brightness.value = v,
                      ),
                    ),
                  ),
                  Icon(Icons.wb_sunny_rounded, color: Colors.white.withValues(alpha: 0.95), size: 20),
                ],
              );
            },
          ),
        ),
      ],
    );
  }
}

class _TalentaBottomPanel extends StatelessWidget {
  const _TalentaBottomPanel({
    required this.step,
    required this.loading,
    required this.notesController,
    required this.canProceed,
    required this.primaryLabel,
    required this.onPrimary,
  });

  final _PunchStep step;
  final bool loading;
  final TextEditingController notesController;
  final bool canProceed;
  final String primaryLabel;
  final VoidCallback onPrimary;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + MediaQuery.paddingOf(context).bottom),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.08),
            blurRadius: 20,
            offset: const Offset(0, -6),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (step == _PunchStep.selfie) ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
              decoration: BoxDecoration(
                color: AppColors.surfaceMuted,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppColors.border),
              ),
              child: TextField(
                controller: notesController,
                maxLines: 2,
                minLines: 1,
                decoration: InputDecoration(
                  hintText: 'Catatan (opsional)',
                  hintStyle: GoogleFonts.plusJakartaSans(color: AppColors.textDim, fontSize: 14),
                  border: InputBorder.none,
                  icon: const Icon(Icons.notes_rounded, color: AppColors.darkGold, size: 20),
                ),
              ),
            ),
            const SizedBox(height: 14),
          ] else
            Padding(
              padding: const EdgeInsets.only(bottom: 14),
              child: Text(
                'Pastikan Anda berada di area kantor sebelum melanjutkan ke verifikasi wajah.',
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 12,
                  color: AppColors.textMuted,
                  height: 1.45,
                ),
                textAlign: TextAlign.center,
              ),
            ),
          AnimatedPress(
            onTap: canProceed && !loading ? onPrimary : null,
            enabled: canProceed && !loading,
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 16),
              decoration: BoxDecoration(
                gradient: canProceed ? AppColors.headerGradient : null,
                color: canProceed ? null : AppColors.border,
                borderRadius: BorderRadius.circular(14),
                boxShadow: canProceed
                    ? [
                        BoxShadow(
                          color: AppColors.chinaRed.withValues(alpha: 0.28),
                          blurRadius: 16,
                          offset: const Offset(0, 6),
                        ),
                      ]
                    : null,
              ),
              child: loading
                  ? const Center(
                      child: SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      ),
                    )
                  : Text(
                      primaryLabel,
                      textAlign: TextAlign.center,
                      style: GoogleFonts.plusJakartaSans(
                        color: canProceed ? Colors.white : AppColors.textDim,
                        fontWeight: FontWeight.w800,
                        fontSize: 16,
                      ),
                    ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PunchPreviewDialog extends StatelessWidget {
  const _PunchPreviewDialog({
    required this.photoBytes,
    required this.capturedAt,
    required this.isClockOut,
    required this.onRetake,
  });

  final Uint8List photoBytes;
  final DateTime capturedAt;
  final bool isClockOut;
  final VoidCallback onRetake;

  @override
  Widget build(BuildContext context) {
    final timeLabel = DateFormat('EEEE, dd MMM yyyy HH:mm').format(capturedAt.toLocal());
    final title = isClockOut ? 'Preview Absen Pulang' : 'Preview Absen Masuk';

    return Dialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: 24),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 22, 20, 20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: const BoxDecoration(
                color: AppColors.successDim,
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.check_rounded, color: AppColors.success, size: 30),
            ),
            const SizedBox(height: 14),
            Text(
              title,
              textAlign: TextAlign.center,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 18,
                fontWeight: FontWeight.w800,
                color: AppColors.text,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Periksa hasil selfie dan waktu sebelum melanjutkan ke rekap absensi.',
              textAlign: TextAlign.center,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 13,
                color: AppColors.textMuted,
                height: 1.45,
              ),
            ),
            const SizedBox(height: 16),
            ClipRRect(
              borderRadius: BorderRadius.circular(14),
              child: AspectRatio(
                aspectRatio: 4 / 3,
                child: Image.memory(photoBytes, fit: BoxFit.cover),
              ),
            ),
            const SizedBox(height: 14),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: AppColors.surfaceMuted,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.border),
              ),
              child: Row(
                children: [
                  const Icon(Icons.schedule_rounded, size: 18, color: AppColors.darkGold),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      timeLabel,
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: AppColors.text,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () {
                      onRetake();
                      Navigator.of(context).pop(false);
                    },
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.text,
                      side: const BorderSide(color: AppColors.border),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    child: Text(
                      'Ambil Ulang',
                      style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w700),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () => Navigator.of(context).pop(true),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.success,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      elevation: 0,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    child: Text(
                      'Konfirmasi',
                      style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w800),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({
    required this.icon,
    required this.label,
    required this.color,
    required this.bg,
  });

  final IconData icon;
  final String label;
  final Color color;
  final Color bg;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.25)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              label,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: color,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
