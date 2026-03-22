"""Tests for the weapon projectile system."""

from spacegame.engine.projectiles import ProjectileManager, WeaponType, Projectile


class TestProjectile:
    """Tests for Projectile dataclass."""

    def test_position_at_start(self) -> None:
        """At progress=0, position is at start."""
        proj = Projectile(
            start_x=100, start_y=200, end_x=500, end_y=200,
            weapon_type=WeaponType.LASER, speed=400,
        )
        assert proj.x == 100
        assert proj.y == 200

    def test_position_at_end(self) -> None:
        """At progress=1, position is at end."""
        proj = Projectile(
            start_x=100, start_y=200, end_x=500, end_y=200,
            weapon_type=WeaponType.LASER, speed=400, progress=1.0,
        )
        assert proj.x == 500
        assert proj.y == 200

    def test_position_midway(self) -> None:
        """At progress=0.5, position is halfway."""
        proj = Projectile(
            start_x=0, start_y=0, end_x=400, end_y=0,
            weapon_type=WeaponType.LASER, speed=400, progress=0.5,
        )
        assert proj.x == 200.0

    def test_arc_height_affects_y(self) -> None:
        """Missile arc should offset Y at midpoint."""
        proj = Projectile(
            start_x=0, start_y=100, end_x=400, end_y=100,
            weapon_type=WeaponType.MISSILE, speed=400,
            progress=0.5, arc_height=40.0,
        )
        # At midpoint, arc is at max: y = 100 - 40 = 60
        assert proj.y == 60.0

    def test_arc_zero_at_endpoints(self) -> None:
        """Arc should be zero at start and end."""
        proj = Projectile(
            start_x=0, start_y=100, end_x=400, end_y=100,
            weapon_type=WeaponType.MISSILE, speed=400, arc_height=40.0,
        )
        proj.progress = 0.0
        assert proj.y == 100.0
        proj.progress = 1.0
        assert proj.y == 100.0

    def test_distance(self) -> None:
        """Distance calculation should be correct."""
        proj = Projectile(
            start_x=0, start_y=0, end_x=300, end_y=400,
            weapon_type=WeaponType.LASER, speed=400,
        )
        assert proj.distance == 500.0


class TestProjectileManager:
    """Tests for ProjectileManager."""

    def test_spawn_laser(self) -> None:
        """Spawning a laser creates one projectile."""
        mgr = ProjectileManager()
        mgr.spawn_laser((0, 0), (400, 0))
        assert mgr.has_active

    def test_spawn_missile(self) -> None:
        """Spawning a missile creates one projectile with arc."""
        mgr = ProjectileManager()
        mgr.spawn_missile((0, 0), (400, 0))
        assert mgr.has_active

    def test_spawn_cannon_burst(self) -> None:
        """Spawning cannon creates multiple rounds."""
        mgr = ProjectileManager()
        mgr.spawn_cannon((0, 0), (400, 0), burst_count=3)
        assert mgr.has_active
        # 3 projectiles + 1 muzzle flash
        assert len(mgr._projectiles) == 3

    def test_projectile_arrives(self) -> None:
        """Projectile should arrive after sufficient update time."""
        mgr = ProjectileManager()
        arrived = False

        def on_impact():
            nonlocal arrived
            arrived = True

        mgr.spawn_laser((0, 0), (400, 0), on_impact=on_impact)
        # Speed=800, distance=400 → 0.5s to arrive
        mgr.update(1.0)  # More than enough time
        assert arrived, "Impact callback should have fired"
        assert not mgr.has_active, "Projectile should be removed after arrival"

    def test_miss_no_callback(self) -> None:
        """Miss projectiles should not trigger impact callback."""
        mgr = ProjectileManager()
        called = False

        def on_impact():
            nonlocal called
            called = True

        mgr.spawn_laser((0, 0), (400, 0), on_impact=on_impact, hit=False)
        mgr.update(2.0)
        assert not called, "Miss should not trigger impact callback"

    def test_clear(self) -> None:
        """Clear removes all projectiles."""
        mgr = ProjectileManager()
        mgr.spawn_laser((0, 0), (400, 0))
        mgr.spawn_missile((0, 0), (400, 0))
        assert mgr.has_active
        mgr.clear()
        assert not mgr.has_active

    def test_multiple_projectiles(self) -> None:
        """Multiple projectiles can coexist."""
        mgr = ProjectileManager()
        mgr.spawn_laser((0, 0), (400, 0))
        mgr.spawn_missile((0, 100), (400, 100))
        assert len(mgr._projectiles) == 2

    def test_muzzle_flash_fades(self) -> None:
        """Muzzle flashes should disappear after their timer."""
        mgr = ProjectileManager()
        mgr.spawn_laser((0, 0), (400, 0))
        assert len(mgr._muzzle_flashes) == 1
        mgr.update(0.2)  # More than flash timer (0.08s)
        assert len(mgr._muzzle_flashes) == 0

    def test_cannon_stagger(self) -> None:
        """Cannon rounds should have staggered progress values."""
        mgr = ProjectileManager()
        mgr.spawn_cannon((0, 0), (400, 0), burst_count=3)
        progresses = [p.progress for p in mgr._projectiles]
        # First round starts at 0, subsequent rounds have negative progress (staggered)
        assert progresses[0] == 0.0
        assert progresses[1] < 0.0
        assert progresses[2] < progresses[1]
