# game/audio.py
"""
Mô-đun Quản lý Âm thanh & Nhạc nền Tự sinh (Procedural Audio & Music Synthesizer):
- Tự tổng hợp toàn bộ hiệu ứng âm thanh (SFX) và giai điệu nhạc nền thư giãn bằng Python thuần
  (math, array, pygame.mixer) mà KHÔNG cần file âm thanh ngoài (.wav/.mp3).
- Bắt ngoại lệ try/except an toàn, tương thích 100% khi chạy ở chế độ headless (dummy audio driver).
- Nhạc nền Pentatonic mộc mạc dịu nhẹ chuẩn Stardew Valley, cùng âm thanh bước chân robot êm tai.
"""

from __future__ import annotations

import array
import math
from typing import Any
import pygame


class SoundAndMusicManager:
    """Quản lý hiệu ứng âm thanh SFX và nhạc nền thư giãn tự tổng hợp."""

    def __init__(self) -> None:
        self.enabled: bool = True
        self.music_enabled: bool = True
        self.bgm_timer: float = 0.0
        self.note_idx: int = 0
        self.step_timer: float = 0.0

        self.mixer_ready: bool = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.bgm_notes: list[pygame.mixer.Sound] = []

        self._init_audio_system()

    def _init_audio_system(self) -> None:
        """Khởi tạo Pygame mixer an toàn và sinh toàn bộ âm thanh vào bộ nhớ."""
        try:
            if not pygame.mixer.get_init():
                # Khởi tạo mixer chuẩn 22050Hz, 16-bit signed, 2 kênh stereo, buffer 512
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

            init_info = pygame.mixer.get_init()
            if init_info:
                sample_rate, _fmt, channels = init_info
                self.mixer_ready = True
                self._synthesize_all_sounds(sample_rate, channels)
                self._synthesize_bgm_notes(sample_rate, channels)
            else:
                self.mixer_ready = False
        except Exception:
            # Chạy an toàn ở môi trường headless không có card âm thanh
            self.mixer_ready = False

    def _synthesize_slide_sound(
        self,
        f0: float,
        f1: float,
        duration: float,
        sample_rate: int,
        channels: int,
        volume: float = 0.22,
        attack_ratio: float = 0.12,
        harmonic_mix: float = 0.0,
    ) -> pygame.mixer.Sound | None:
        """Sinh âm thanh trượt tần số tuyến tính từ f0 đến f1 có envelope mượt mà."""
        try:
            n_samples = max(1, int(sample_rate * duration))
            raw_data = array.array("h")
            freq_diff = f1 - f0

            for i in range(n_samples):
                t = i / sample_rate
                # Tích phân pha sóng sin liên tục: theta(t) = 2*pi*(f0*t + ((f1-f0)/(2*dur))*t^2)
                phase = 2.0 * math.pi * (f0 * t + (freq_diff / (2.0 * duration)) * (t * t))
                val = math.sin(phase)
                if harmonic_mix > 0.0:
                    val += harmonic_mix * math.sin(2.0 * phase)

                # Envelope: mượt ở đầu (attack) và giảm dần về 0 ở đuôi (decay)
                progress = i / max(1, n_samples)
                if progress < attack_ratio:
                    env = progress / attack_ratio
                else:
                    env = 1.0 - (progress - attack_ratio) / (1.0 - attack_ratio)
                env = max(0.0, min(1.0, env))

                samp = int(val * env * volume * 32767.0)
                samp = max(-32767, min(32767, samp))

                for _ in range(channels):
                    raw_data.append(samp)

            return pygame.mixer.Sound(buffer=raw_data)
        except Exception:
            return None

    def _synthesize_notes_sequence(
        self,
        notes: list[tuple[float, float]],
        sample_rate: int,
        channels: int,
        volume: float = 0.22,
        harmonic_mix: float = 0.12,
    ) -> pygame.mixer.Sound | None:
        """Sinh chuỗi nốt nhạc kế tiếp nhau với envelope chuông gõ (percussive decay)."""
        try:
            raw_data = array.array("h")
            for freq, dur in notes:
                n_samples = max(1, int(sample_rate * dur))
                for i in range(n_samples):
                    t = i / sample_rate
                    phase = 2.0 * math.pi * freq * t
                    val = math.sin(phase)
                    if harmonic_mix > 0.0:
                        val += harmonic_mix * math.sin(2.0 * phase)

                    # Envelope: gõ nhanh 10% rồi giảm theo hàm số mũ
                    p = i / max(1, n_samples)
                    if p < 0.10:
                        env = p / 0.10
                    else:
                        env = math.exp(-3.2 * (p - 0.10))
                    env = max(0.0, min(1.0, env))

                    samp = int(val * env * volume * 32767.0)
                    samp = max(-32767, min(32767, samp))

                    for _ in range(channels):
                        raw_data.append(samp)

            return pygame.mixer.Sound(buffer=raw_data)
        except Exception:
            return None

    def _synthesize_all_sounds(self, sample_rate: int, channels: int) -> None:
        """Sinh trước 8 hiệu ứng âm thanh trò chơi chuẩn Stardew Valley."""
        # 1. "step": Tiếng bước chân / bánh xe lăn rất êm (50ms, tần số trầm 180Hz)
        snd_step = self._synthesize_slide_sound(
            f0=180.0,
            f1=160.0,
            duration=0.050,
            sample_rate=sample_rate,
            channels=channels,
            volume=0.14,
            attack_ratio=0.15,
        )
        if snd_step:
            self.sounds["step"] = snd_step

        # 2. "harvest": Tiếng hái quả / nhặt vật phẩm giòn tan (90ms, trượt tần số 440Hz -> 660Hz)
        snd_harvest = self._synthesize_slide_sound(
            f0=440.0,
            f1=660.0,
            duration=0.090,
            sample_rate=sample_rate,
            channels=channels,
            volume=0.22,
            attack_ratio=0.10,
        )
        if snd_harvest:
            self.sounds["harvest"] = snd_harvest

        # 3. "cast": Tiếng quăng dây câu xuống nước (110ms, 520Hz -> 300Hz)
        snd_cast = self._synthesize_slide_sound(
            f0=520.0,
            f1=300.0,
            duration=0.110,
            sample_rate=sample_rate,
            channels=channels,
            volume=0.20,
            attack_ratio=0.08,
        )
        if snd_cast:
            self.sounds["cast"] = snd_cast

        # 4. "bite": Tiếng phao câu cá giật báo hiệu [!!] (140ms, 2 nốt 784Hz -> 987Hz)
        snd_bite = self._synthesize_notes_sequence(
            notes=[(784.0, 0.070), (987.0, 0.070)],
            sample_rate=sample_rate,
            channels=channels,
            volume=0.25,
            harmonic_mix=0.15,
        )
        if snd_bite:
            self.sounds["bite"] = snd_bite

        # 5. "gold": Tiếng đồng xu vàng ting-ting! chuẩn Stardew Valley (180ms, 2 nốt cao 1046Hz -> 1318Hz)
        snd_gold = self._synthesize_notes_sequence(
            notes=[(1046.0, 0.090), (1318.0, 0.090)],
            sample_rate=sample_rate,
            channels=channels,
            volume=0.22,
            harmonic_mix=0.20,
        )
        if snd_gold:
            self.sounds["gold"] = snd_gold

        # 6. "heart": Hợp âm ấm áp khi lên Tim thiện cảm hoặc hoàn thành đơn (240ms, 523Hz -> 659Hz -> 784Hz)
        snd_heart = self._synthesize_notes_sequence(
            notes=[(523.25, 0.080), (659.25, 0.080), (784.00, 0.080)],
            sample_rate=sample_rate,
            channels=channels,
            volume=0.22,
            harmonic_mix=0.18,
        )
        if snd_heart:
            self.sounds["heart"] = snd_heart

        # 7. "bump": Tiếng trầm cảnh báo khi va chạm (160ms, 140Hz -> 90Hz)
        snd_bump = self._synthesize_slide_sound(
            f0=140.0,
            f1=90.0,
            duration=0.160,
            sample_rate=sample_rate,
            channels=channels,
            volume=0.28,
            attack_ratio=0.06,
            harmonic_mix=0.25,
        )
        if snd_bump:
            self.sounds["bump"] = snd_bump

        # 8. "portal": Tiếng chuyển vùng nhẹ nhàng (120ms, 392Hz -> 523Hz)
        snd_portal = self._synthesize_slide_sound(
            f0=392.0,
            f1=523.25,
            duration=0.120,
            sample_rate=sample_rate,
            channels=channels,
            volume=0.20,
            attack_ratio=0.12,
        )
        if snd_portal:
            self.sounds["portal"] = snd_portal

    def _synthesize_bgm_notes(self, sample_rate: int, channels: int) -> None:
        """Sinh các nốt nhạc pentatonic êm ái như tiếng đàn marimba/kalimba thư giãn."""
        # Giai điệu ngũ cung thư thái: G4, A4, C5, D5, E5, G5, E5, D5, C5, A4
        pitches = [
            392.00,  # G4
            440.00,  # A4
            523.25,  # C5
            587.33,  # D5
            659.25,  # E5
            784.00,  # G5
            659.25,  # E5
            587.33,  # D5
            523.25,  # C5
            440.00,  # A4
        ]
        note_duration = 0.55
        for freq in pitches:
            snd = self._synthesize_notes_sequence(
                notes=[(freq, note_duration)],
                sample_rate=sample_rate,
                channels=channels,
                volume=0.08,  # Âm lượng nhỏ 0.08 rất dịu nhẹ theo yêu cầu
                harmonic_mix=0.12,
            )
            if snd:
                self.bgm_notes.append(snd)

    def play_sfx(self, name: str) -> None:
        """Phát hiệu ứng âm thanh tương ứng nếu hệ thống âm thanh đang bật và mixer đã sẵn sàng."""
        if not self.enabled or not self.mixer_ready:
            return
        sound = self.sounds.get(name)
        if sound is not None:
            try:
                sound.play()
            except Exception:
                pass

    def toggle_mute(self) -> bool:
        """Bật/tắt toàn bộ âm thanh (SFX + Nhạc nền) bằng phím tắt [B]."""
        self.enabled = not self.enabled
        self.music_enabled = self.enabled
        return self.enabled

    def toggle_music(self) -> bool:
        """Bật/tắt riêng nhạc nền thư giãn."""
        self.music_enabled = not self.music_enabled
        return self.music_enabled

    def update(self, game: Any, dt: float) -> None:
        """Cập nhật phát nốt nhạc nền mỗi 1.8s và tiếng bước chân robot khi di chuyển."""
        if not self.mixer_ready:
            return

        # 1. Phát nốt nhạc nền thư giãn mỗi 1.8s khi self.music_enabled
        if self.music_enabled and self.bgm_notes:
            self.bgm_timer += dt
            if self.bgm_timer >= 1.8:
                self.bgm_timer = 0.0
                note_sound = self.bgm_notes[self.note_idx % len(self.bgm_notes)]
                self.note_idx = (self.note_idx + 1) % len(self.bgm_notes)
                try:
                    note_sound.play()
                except Exception:
                    pass

        # 2. Phát tiếng bước chân / bánh xe lăn nhẹ mỗi 0.38s khi Robot đang di chuyển
        if self.enabled:
            robot = getattr(game, "robot", None)
            v_mps = float(getattr(robot, "v_mps", 0.0)) if robot is not None else 0.0
            if v_mps > 0.1:
                self.step_timer += dt
                if self.step_timer >= 0.38:
                    self.step_timer = 0.0
                    self.play_sfx("step")
            else:
                self.step_timer = min(self.step_timer, 0.38)
