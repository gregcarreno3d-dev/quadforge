//! Deterministic hash collections.
//!
//! The standard `HashMap`/`HashSet` seed their hasher randomly on every run, so iterating one gives a different
//! order each time and the engine could return different results for the same input. These aliases use a fixed
//! hasher: same input, same insertion order, same output. Use them instead of `std::collections::HashMap`.

use std::collections::hash_map::DefaultHasher;
use std::hash::BuildHasherDefault;

pub type HashMap<K, V> = std::collections::HashMap<K, V, BuildHasherDefault<DefaultHasher>>;
pub type HashSet<K> = std::collections::HashSet<K, BuildHasherDefault<DefaultHasher>>;
