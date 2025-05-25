<template>
    <div class="map">
        <!-- Map content goes here -->
    </div>
</template>

<script>
export default {
    name: "Map",
    data() {
        return {
            // Component data
        };
    },
    methods: {
        // Component methods
    },
    mounted() {
        // Lifecycle hook
    const map = L.map(this.$el.querySelector('.map')).setView([53.5511, 9.9937], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
};
</script>

