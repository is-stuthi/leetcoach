"""
The ~40-problem practice catalog shared by two different features:
- seed.py uses it plus fake solved/confidence/revision history for the demo account
- routes/problems.py's "load sample problems" uses it bare (unsolved, no
  fake history) so a brand-new account with no real LeetCode profile still
  has real problems to practice against instead of an empty app.
"""

# (leetcode_id, title, difficulty, topics, slug)
SAMPLE_PROBLEMS = [
    (1, "Two Sum", "Easy", ["Array", "Hash Table"], "two-sum"),
    (121, "Best Time to Buy and Sell Stock", "Easy", ["Array"], "best-time-to-buy-and-sell-stock"),
    (217, "Contains Duplicate", "Easy", ["Array", "Hash Table"], "contains-duplicate"),
    (238, "Product of Array Except Self", "Medium", ["Array"], "product-of-array-except-self"),
    (53, "Maximum Subarray", "Medium", ["Array"], "maximum-subarray"),
    (56, "Merge Intervals", "Medium", ["Array"], "merge-intervals"),
    (49, "Group Anagrams", "Medium", ["Array", "Hash Table"], "group-anagrams"),
    (347, "Top K Frequent Elements", "Medium", ["Hash Table", "Heap / Priority Queue"], "top-k-frequent-elements"),
    (242, "Valid Anagram", "Easy", ["Hash Table"], "valid-anagram"),
    (125, "Valid Palindrome", "Easy", ["Two Pointers"], "valid-palindrome"),
    (15, "3Sum", "Medium", ["Array", "Two Pointers"], "3sum"),
    (11, "Container With Most Water", "Medium", ["Two Pointers"], "container-with-most-water"),
    (42, "Trapping Rain Water", "Hard", ["Two Pointers", "Array"], "trapping-rain-water"),
    (3, "Longest Substring Without Repeating Characters", "Medium", ["Sliding Window", "Hash Table"], "longest-substring-without-repeating-characters"),
    (76, "Minimum Window Substring", "Hard", ["Sliding Window", "Hash Table"], "minimum-window-substring"),
    (424, "Longest Repeating Character Replacement", "Medium", ["Sliding Window"], "longest-repeating-character-replacement"),
    (239, "Sliding Window Maximum", "Hard", ["Sliding Window", "Heap / Priority Queue"], "sliding-window-maximum"),
    (206, "Reverse Linked List", "Easy", ["Linked List"], "reverse-linked-list"),
    (21, "Merge Two Sorted Lists", "Easy", ["Linked List"], "merge-two-sorted-lists"),
    (141, "Linked List Cycle", "Easy", ["Linked List"], "linked-list-cycle"),
    (19, "Remove Nth Node From End of List", "Medium", ["Linked List", "Two Pointers"], "remove-nth-node-from-end-of-list"),
    (704, "Binary Search", "Easy", ["Binary Search"], "binary-search"),
    (33, "Search in Rotated Sorted Array", "Medium", ["Binary Search"], "search-in-rotated-sorted-array"),
    (153, "Find Minimum in Rotated Sorted Array", "Medium", ["Binary Search"], "find-minimum-in-rotated-sorted-array"),
    (875, "Koko Eating Bananas", "Medium", ["Binary Search"], "koko-eating-bananas"),
    (226, "Invert Binary Tree", "Easy", ["Trees"], "invert-binary-tree"),
    (104, "Maximum Depth of Binary Tree", "Easy", ["Trees"], "maximum-depth-of-binary-tree"),
    (102, "Binary Tree Level Order Traversal", "Medium", ["Trees"], "binary-tree-level-order-traversal"),
    (98, "Validate Binary Search Tree", "Medium", ["Trees"], "validate-binary-search-tree"),
    (235, "Lowest Common Ancestor of a BST", "Medium", ["Trees"], "lowest-common-ancestor-of-a-binary-search-tree"),
    (200, "Number of Islands", "Medium", ["Graphs"], "number-of-islands"),
    (133, "Clone Graph", "Medium", ["Graphs"], "clone-graph"),
    (207, "Course Schedule", "Medium", ["Graphs"], "course-schedule"),
    (215, "Kth Largest Element in an Array", "Medium", ["Heap / Priority Queue"], "kth-largest-element-in-an-array"),
    (621, "Task Scheduler", "Medium", ["Heap / Priority Queue"], "task-scheduler"),
    (70, "Climbing Stairs", "Easy", ["Dynamic Programming"], "climbing-stairs"),
    (198, "House Robber", "Medium", ["Dynamic Programming"], "house-robber"),
    (322, "Coin Change", "Medium", ["Dynamic Programming"], "coin-change"),
    (300, "Longest Increasing Subsequence", "Medium", ["Dynamic Programming"], "longest-increasing-subsequence"),
    (139, "Word Break", "Medium", ["Dynamic Programming", "Hash Table"], "word-break"),
]
